"""Tests for ESigningSubmission CRUD, resend, and DocuSeal webhook."""
import hashlib
import hmac
import json
from unittest import mock

from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.esigning.models import ESigningSubmission
from tests.base import TremlyAPITestCase


class ESigningListCreateTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)

    def test_list_submissions(self):
        ESigningSubmission.objects.create(
            lease=self.lease, status="pending", created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_filter_by_lease(self):
        ESigningSubmission.objects.create(
            lease=self.lease, status="pending", created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-list"), {"lease_id": self.lease.pk})
        self.assertEqual(resp.status_code, 200)
        for item in resp.data["results"]:
            self.assertEqual(item["lease"], self.lease.pk)

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_create_success(self, mock_create):
        mock_create.return_value = {
            "template": {"id": "tmpl_123"},
            "submission": [
                {
                    "id": 1,
                    "submission_id": "sub_123",
                    "name": "Tenant",
                    "email": "tenant@test.com",
                    "role": "First Party",
                    "status": "sent",
                    "slug": "abc",
                    "embed_src": "https://example.com/embed",
                }
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [{"name": "Tenant", "email": "tenant@test.com", "role": "First Party"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        # Default signing_mode is sequential
        self.assertEqual(resp.data["signing_mode"], "sequential")
        mock_create.assert_called_once()
        # Verify signing_mode was passed through to the service
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get("signing_mode"), "sequential")

    def test_create_no_lease_id(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {"signers": [{"name": "T", "email": "t@test.com"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_no_signers(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {"lease_id": self.lease.pk, "signers": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invalid_lease(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {"lease_id": 99999, "signers": [{"name": "T", "email": "t@test.com"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_tenant_cannot_create_submission(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [{"name": "X", "email": "x@test.com"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_agent_cannot_create_for_lease_outside_portfolio(self, mock_create):
        other_agent = self.create_agent(email="other_agent@test.com")
        other_prop = self.create_property(agent=other_agent, name="Other Prop")
        other_unit = self.create_unit(property_obj=other_prop, unit_number="X1")
        other_lease = self.create_lease(unit=other_unit)

        mock_create.return_value = {
            "template": {"id": "tmpl_x"},
            "submission": [
                {
                    "id": 1,
                    "submission_id": "sub_x",
                    "name": "T",
                    "email": "t@test.com",
                    "status": "sent",
                    "slug": "a",
                    "embed_src": "",
                }
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {"lease_id": other_lease.pk, "signers": [{"name": "T", "email": "t@test.com"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
        mock_create.assert_not_called()

    @mock.patch("apps.esigning.views.services.create_lease_submission", side_effect=Exception("DocuSeal down"))
    def test_docuseal_error(self, mock_create):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [{"name": "T", "email": "t@test.com"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 502)

    def test_unauthenticated(self):
        resp = self.client.get(reverse("esigning-list"))
        self.assertEqual(resp.status_code, 401)


class ESigningWebhookInfoTests(TremlyAPITestCase):
    def setUp(self):
        self.agent = self.create_agent()

    def test_agent_gets_webhook_info(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-webhook-info"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("webhook_url", resp.data)
        self.assertIn("verify_mode", resp.data)
        self.assertTrue(resp.data["webhook_url"].endswith("/api/v1/esigning/webhook/"))

    def test_tenant_forbidden(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(reverse("esigning-webhook-info"))
        self.assertEqual(resp.status_code, 403)


class ESigningDetailTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_100",
            status="pending",
            created_by=self.agent,
        )

    def test_retrieve(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[self.submission.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["docuseal_submission_id"], "sub_100")

    def test_retrieve_not_found(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[99999]))
        self.assertEqual(resp.status_code, 404)


class ESigningResendTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease, status="pending", created_by=self.agent,
        )

    @mock.patch("requests.post")
    def test_resend_success(self, mock_post):
        mock_resp = mock.MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"submitter_id": 42},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])

    def test_resend_no_submitter_id(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("requests.post", side_effect=Exception("timeout"))
    def test_resend_api_error(self, mock_post):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"submitter_id": 42},
            format="json",
        )
        self.assertEqual(resp.status_code, 502)


class ESigningPublicLinkTests(TremlyAPITestCase):
    """UUID passwordless signing links for the admin /sign/:token page."""

    def setUp(self):
        from apps.esigning.models import ESigningPublicLink

        self._ESigningPublicLink = ESigningPublicLink
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_pl",
            status="pending",
            created_by=self.agent,
            signers=[
                {
                    "id": 99,
                    "name": "Tenant",
                    "email": "t@test.com",
                    "status": "sent",
                    "embed_src": "https://docuseal.example.com/embed/99",
                    "order": 0,
                },
            ],
        )

    def test_create_public_link_as_agent(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"submitter_id": 99},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("uuid", resp.data)
        self.assertIn("sign_path", resp.data)
        self.assertIs(resp.data.get("email_sent"), False)
        self.assertTrue(self._ESigningPublicLink.objects.filter(submitter_id=99).exists())

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_public_link_send_email(self, mock_send):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {
                "submitter_id": 99,
                "send_email": True,
                "public_app_origin": "https://admin.example.com",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["email_sent"])
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][2], "t@test.com")

    def test_public_link_send_email_requires_absolute_url(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"submitter_id": 99, "send_email": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("public_app_origin", resp.data["error"])

    def test_public_link_send_email_requires_signer_email(self):
        self.submission.signers = [
            {
                "id": 98,
                "name": "No Mail",
                "email": "",
                "status": "sent",
                "embed_src": "https://docuseal.example.com/embed/98",
                "order": 0,
            },
        ]
        self.submission.save()
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {
                "submitter_id": 98,
                "send_email": True,
                "public_app_origin": "https://admin.example.com",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data["error"].lower())

    def test_create_public_link_unknown_submitter(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"submitter_id": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_public_sign_detail_no_auth(self):
        from datetime import timedelta

        from django.utils import timezone

        link = self._ESigningPublicLink.objects.create(
            submission=self.submission,
            submitter_id=99,
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.client.get(reverse("esigning-public-sign", kwargs={"link_id": link.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["embed_src"], "https://docuseal.example.com/embed/99")
        self.assertIn("document_title", resp.data)

    def test_public_sign_expired(self):
        from datetime import timedelta

        from django.utils import timezone

        link = self._ESigningPublicLink.objects.create(
            submission=self.submission,
            submitter_id=99,
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp = self.client.get(reverse("esigning-public-sign", kwargs={"link_id": link.pk}))
        self.assertEqual(resp.status_code, 410)

    def test_tenant_cannot_create_public_link(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"submitter_id": 99},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


class ESigningTenantAccessTests(TremlyAPITestCase):
    """Tenants may list/retrieve submissions only for their leases; no create/resend."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.tenant_user = self.create_tenant(email="tenantaccess@test.com")
        self.person = self.create_person(
            full_name="Tenant Access",
            linked_user=self.tenant_user,
            email="tenantaccess@test.com",
        )
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.person)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_tenant",
            status="pending",
            created_by=self.agent,
            signers=[
                {"id": 1, "email": "tenantaccess@test.com", "status": "sent", "order": 0},
            ],
        )

    def test_tenant_lists_own_lease_submissions(self):
        self.authenticate(self.tenant_user)
        resp = self.client.get(reverse("esigning-list"), {"lease_id": self.lease.pk})
        self.assertEqual(resp.status_code, 200)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.submission.pk, ids)

    def test_tenant_does_not_see_other_lease_submissions(self):
        other_prop = self.create_property(agent=self.agent, name="Other")
        other_unit = self.create_unit(property_obj=other_prop, unit_number="Z9")
        other_lease = self.create_lease(unit=other_unit)
        other_sub = ESigningSubmission.objects.create(
            lease=other_lease,
            docuseal_submission_id="sub_other",
            status="pending",
            created_by=self.agent,
        )
        self.authenticate(self.tenant_user)
        resp = self.client.get(reverse("esigning-list"))
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.submission.pk, ids)
        self.assertNotIn(other_sub.pk, ids)

    def test_tenant_retrieve_own(self):
        self.authenticate(self.tenant_user)
        resp = self.client.get(reverse("esigning-detail", args=[self.submission.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_tenant_retrieve_other_404(self):
        other_prop = self.create_property(agent=self.agent, name="Other2")
        other_unit = self.create_unit(property_obj=other_prop, unit_number="Z8")
        other_lease = self.create_lease(unit=other_unit)
        other_sub = ESigningSubmission.objects.create(
            lease=other_lease,
            docuseal_submission_id="sub_other2",
            status="pending",
            created_by=self.agent,
        )
        self.authenticate(self.tenant_user)
        resp = self.client.get(reverse("esigning-detail", args=[other_sub.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_tenant_resend_forbidden(self):
        self.authenticate(self.tenant_user)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"submitter_id": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


class DocuSealWebhookTests(TestCase):
    """Webhook tests use Django TestCase (no DRF auth needed)."""

    def setUp(self):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.leases.models import Lease
        from datetime import date, timedelta
        from decimal import Decimal

        self.agent = User.objects.create_user(email="wh@test.com", password="pass", role="agent")
        prop = Property.objects.create(name="WH Prop", agent=self.agent, property_type="apartment")
        unit = Unit.objects.create(property=prop, unit_number="1", rent_amount=Decimal("5000"))
        lease = Lease.objects.create(
            unit=unit, start_date=date.today(), end_date=date.today() + timedelta(days=365),
            monthly_rent=Decimal("5000"), deposit=Decimal("10000"), status="active",
        )
        self.submission = ESigningSubmission.objects.create(
            lease=lease,
            docuseal_submission_id="sub_200",
            status="pending",
            signers=[{"id": 1, "name": "Tenant", "status": "sent"}],
            created_by=self.agent,
        )

    def _post_webhook(self, payload, headers=None):
        body = json.dumps(payload)
        kwargs = {"content_type": "application/json", "data": body}
        if headers:
            for k, v in headers.items():
                kwargs[k] = v
        return self.client.post(reverse("esigning-webhook"), **kwargs)

    def test_webhook_completed(self):
        resp = self._post_webhook({
            "event_type": "submission.completed",
            "data": {
                "submission_id": "sub_200",
                "audit_log_url": "https://example.com/audit.pdf",
                "submitters": [{"id": 1, "status": "completed", "completed_at": "2026-03-01T00:00:00Z"}],
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "completed")
        self.assertEqual(self.submission.signed_pdf_url, "https://example.com/audit.pdf")

    def test_webhook_declined(self):
        resp = self._post_webhook({
            "event_type": "submission.declined",
            "data": {"submission_id": "sub_200"},
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "declined")

    def test_webhook_viewed(self):
        resp = self._post_webhook({
            "event_type": "form.viewed",
            "data": {"submission_id": "sub_200"},
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "in_progress")

    def test_webhook_unknown_submission(self):
        resp = self._post_webhook({
            "event_type": "submission.completed",
            "data": {"submission_id": "unknown_999"},
        })
        self.assertEqual(resp.status_code, 200)  # Returns 'ok' silently

    def test_webhook_bad_json(self):
        resp = self.client.post(
            reverse("esigning-webhook"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_get_reachable(self):
        resp = self.client.get(reverse("esigning-webhook"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("detail", resp.json())

    def test_webhook_static_header_ok(self):
        with self.settings(
            DOCUSEAL_WEBHOOK_SECRET="shh",
            DOCUSEAL_WEBHOOK_HEADER_NAME="X-Tremly-Token",
        ):
            resp = self.client.post(
                reverse("esigning-webhook"),
                data=json.dumps({
                    "event_type": "form.viewed",
                    "data": {"submission_id": "sub_200"},
                }),
                content_type="application/json",
                HTTP_X_TREMLY_TOKEN="shh",
            )
        self.assertEqual(resp.status_code, 200)

    def test_webhook_static_header_bad(self):
        with self.settings(
            DOCUSEAL_WEBHOOK_SECRET="shh",
            DOCUSEAL_WEBHOOK_HEADER_NAME="X-Tremly-Token",
        ):
            resp = self.client.post(
                reverse("esigning-webhook"),
                data=json.dumps({"event_type": "form.viewed", "data": {"submission_id": "sub_200"}}),
                content_type="application/json",
                HTTP_X_TREMLY_TOKEN="wrong",
            )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.esigning.webhooks.settings")
    def test_webhook_no_signature_when_no_secret(self, mock_settings):
        """
        SECURITY AUDIT (vuln #10): If DOCUSEAL_WEBHOOK_SECRET is not set,
        signature verification is skipped entirely.
        """
        mock_settings.DOCUSEAL_WEBHOOK_SECRET = ""
        # Should process without any signature header
        resp = self._post_webhook({
            "event_type": "form.viewed",
            "data": {"submission_id": "sub_200"},
        })
        self.assertEqual(resp.status_code, 200)

    def test_webhook_valid_signature(self):
        secret = "test-webhook-secret"
        payload = json.dumps({
            "event_type": "form.viewed",
            "data": {"submission_id": "sub_200"},
        })
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        with self.settings(DOCUSEAL_WEBHOOK_SECRET=secret):
            resp = self.client.post(
                reverse("esigning-webhook"),
                data=payload,
                content_type="application/json",
                HTTP_X_DOCUSEAL_SIGNATURE=sig,
            )
        self.assertEqual(resp.status_code, 200)

    def test_webhook_invalid_signature(self):
        secret = "test-webhook-secret"
        with self.settings(DOCUSEAL_WEBHOOK_SECRET=secret):
            resp = self._post_webhook(
                {"event_type": "form.viewed", "data": {"submission_id": "sub_200"}},
                headers={"HTTP_X_DOCUSEAL_SIGNATURE": "badsig"},
            )
        self.assertEqual(resp.status_code, 400)

    def test_webhook_form_completed_updates_single_signer(self):
        """form.completed fires per-signer; only that signer should update."""
        self.submission.signers = [
            {"id": 1, "name": "Landlord", "status": "sent", "order": 0},
            {"id": 2, "name": "Tenant", "status": "sent", "order": 1},
        ]
        self.submission.signing_mode = "sequential"
        self.submission.save()

        resp = self._post_webhook({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_200",
                "submitter": {"id": 1, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        # Overall status should be in_progress (not completed — second signer hasn't signed)
        self.assertEqual(self.submission.status, "in_progress")
        # First signer completed, second still sent
        self.assertEqual(self.submission.signers[0]["status"], "completed")
        self.assertEqual(self.submission.signers[0]["completed_at"], "2026-03-20T10:00:00Z")
        self.assertEqual(self.submission.signers[1]["status"], "sent")

    def test_webhook_declined_marks_specific_signer(self):
        """When a signer declines, the specific signer record should be updated."""
        self.submission.signers = [
            {"id": 1, "name": "Landlord", "status": "completed", "order": 0},
            {"id": 2, "name": "Tenant", "status": "sent", "order": 1},
        ]
        self.submission.save()

        resp = self._post_webhook({
            "event_type": "submission.declined",
            "data": {
                "submission_id": "sub_200",
                "submitter": {"id": 2},
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "declined")
        self.assertEqual(self.submission.signers[1]["status"], "declined")
        # First signer should remain completed
        self.assertEqual(self.submission.signers[0]["status"], "completed")

    def test_webhook_viewed_tracks_signer(self):
        """form.viewed should mark the specific signer as opened."""
        self.submission.signers = [
            {"id": 1, "name": "Landlord", "status": "sent", "order": 0},
        ]
        self.submission.save()

        resp = self._post_webhook({
            "event_type": "form.viewed",
            "data": {
                "submission_id": "sub_200",
                "submitter": {"id": 1},
            },
        })
        self.assertEqual(resp.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.signers[0]["status"], "opened")


class SequentialSigningTests(TremlyAPITestCase):
    """Tests for sequential signing workflow."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_create_sequential_default(self, mock_create):
        """Default signing_mode should be 'sequential'."""
        mock_create.return_value = {
            "template": {"id": "tmpl_1"},
            "submission": [
                {"id": 10, "submission_id": "sub_seq", "name": "Landlord",
                 "email": "ll@test.com", "role": "First Party", "status": "sent",
                 "slug": "a", "embed_src": "", "order": 0},
                {"id": 11, "submission_id": "sub_seq", "name": "Tenant",
                 "email": "t@test.com", "role": "Second Party", "status": "sent",
                 "slug": "b", "embed_src": "", "order": 1},
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [
                    {"name": "Landlord", "email": "ll@test.com", "role": "First Party"},
                    {"name": "Tenant", "email": "t@test.com", "role": "Second Party"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["signing_mode"], "sequential")
        # Signers should be ordered
        signers = resp.data["signers"]
        self.assertEqual(signers[0]["order"], 0)
        self.assertEqual(signers[1]["order"], 1)
        self.assertEqual(signers[0]["name"], "Landlord")
        self.assertEqual(signers[1]["name"], "Tenant")

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_create_parallel_mode(self, mock_create):
        """Explicit parallel mode — no order enforcement."""
        mock_create.return_value = {
            "template": {"id": "tmpl_2"},
            "submission": [
                {"id": 20, "submission_id": "sub_par", "name": "Landlord",
                 "email": "ll@test.com", "status": "sent", "slug": "a", "embed_src": ""},
                {"id": 21, "submission_id": "sub_par", "name": "Tenant",
                 "email": "t@test.com", "status": "sent", "slug": "b", "embed_src": ""},
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signing_mode": "parallel",
                "signers": [
                    {"name": "Landlord", "email": "ll@test.com"},
                    {"name": "Tenant", "email": "t@test.com"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["signing_mode"], "parallel")
        # Parallel — signing_mode passed to service
        _, kwargs = mock_create.call_args
        self.assertEqual(kwargs["signing_mode"], "parallel")

    def test_create_invalid_signing_mode(self):
        """Reject unknown signing_mode values."""
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signing_mode": "round_robin",
                "signers": [{"name": "T", "email": "t@test.com"}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("signing_mode", resp.data["error"])

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_sequential_signer_order_preserved(self, mock_create):
        """Signers stored in order they were submitted (or by explicit order)."""
        mock_create.return_value = {
            "template": {"id": "tmpl_3"},
            "submission": [
                {"id": 30, "submission_id": "sub_ord", "name": "Witness",
                 "email": "w@test.com", "status": "sent", "slug": "c", "embed_src": "", "order": 2},
                {"id": 31, "submission_id": "sub_ord", "name": "Landlord",
                 "email": "ll@test.com", "status": "sent", "slug": "a", "embed_src": "", "order": 0},
                {"id": 32, "submission_id": "sub_ord", "name": "Tenant",
                 "email": "t@test.com", "status": "sent", "slug": "b", "embed_src": "", "order": 1},
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [
                    {"name": "Witness", "email": "w@test.com", "order": 2},
                    {"name": "Landlord", "email": "ll@test.com", "order": 0},
                    {"name": "Tenant", "email": "t@test.com", "order": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        signers = resp.data["signers"]
        # Should be sorted by order: Landlord (0) → Tenant (1) → Witness (2)
        self.assertEqual(signers[0]["name"], "Landlord")
        self.assertEqual(signers[1]["name"], "Tenant")
        self.assertEqual(signers[2]["name"], "Witness")

    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_sequential_three_signers_workflow(self, mock_create):
        """
        Full sequential workflow: Landlord signs → Tenant signs → Witness signs.
        Verify per-signer webhook updates track the chain correctly.
        """
        mock_create.return_value = {
            "template": {"id": "tmpl_4"},
            "submission": [
                {"id": 40, "submission_id": "sub_chain", "name": "Landlord",
                 "email": "ll@test.com", "status": "sent", "slug": "a", "embed_src": "", "order": 0},
                {"id": 41, "submission_id": "sub_chain", "name": "Tenant",
                 "email": "t@test.com", "status": "sent", "slug": "b", "embed_src": "", "order": 1},
                {"id": 42, "submission_id": "sub_chain", "name": "Witness",
                 "email": "w@test.com", "status": "sent", "slug": "c", "embed_src": "", "order": 2},
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            {
                "lease_id": self.lease.pk,
                "signers": [
                    {"name": "Landlord", "email": "ll@test.com"},
                    {"name": "Tenant", "email": "t@test.com"},
                    {"name": "Witness", "email": "w@test.com"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        sub = ESigningSubmission.objects.get(docuseal_submission_id="sub_chain")

        # Step 1: Landlord views the form
        self.client.post(
            reverse("esigning-webhook"),
            json.dumps({
                "event_type": "form.viewed",
                "data": {"submission_id": "sub_chain", "submitter": {"id": 40}},
            }),
            content_type="application/json",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.status, "in_progress")
        self.assertEqual(sub.signers[0]["status"], "opened")
        self.assertEqual(sub.signers[1]["status"], "sent")  # Tenant still waiting

        # Step 2: Landlord signs
        self.client.post(
            reverse("esigning-webhook"),
            json.dumps({
                "event_type": "form.completed",
                "data": {
                    "submission_id": "sub_chain",
                    "submitter": {"id": 40, "completed_at": "2026-03-20T10:00:00Z"},
                },
            }),
            content_type="application/json",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.status, "in_progress")
        self.assertEqual(sub.signers[0]["status"], "completed")
        self.assertEqual(sub.signers[1]["status"], "sent")  # Tenant's turn next

        # Step 3: Tenant signs
        self.client.post(
            reverse("esigning-webhook"),
            json.dumps({
                "event_type": "form.completed",
                "data": {
                    "submission_id": "sub_chain",
                    "submitter": {"id": 41, "completed_at": "2026-03-21T14:00:00Z"},
                },
            }),
            content_type="application/json",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.signers[1]["status"], "completed")
        self.assertEqual(sub.signers[2]["status"], "sent")  # Witness's turn

        # Step 4: Witness signs — DocuSeal sends submission.completed
        self.client.post(
            reverse("esigning-webhook"),
            json.dumps({
                "event_type": "submission.completed",
                "data": {
                    "submission_id": "sub_chain",
                    "audit_log_url": "https://docuseal.com/audit/final.pdf",
                    "submitters": [
                        {"id": 40, "status": "completed", "completed_at": "2026-03-20T10:00:00Z"},
                        {"id": 41, "status": "completed", "completed_at": "2026-03-21T14:00:00Z"},
                        {"id": 42, "status": "completed", "completed_at": "2026-03-22T09:00:00Z"},
                    ],
                },
            }),
            content_type="application/json",
        )
        sub.refresh_from_db()
        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.signed_pdf_url, "https://docuseal.com/audit/final.pdf")
        # All three signers completed
        for signer in sub.signers:
            self.assertEqual(signer["status"], "completed")
            self.assertIsNotNone(signer["completed_at"])

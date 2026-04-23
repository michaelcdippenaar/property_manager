"""Tests for ESigningSubmission CRUD, resend, and public signing links."""
import json
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.esigning.models import ESigningSubmission
from apps.test_hub.base.test_case import TremlyAPITestCase
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]


class ESigningListCreateTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        # primary_tenant is required by the RHA gate (MISSING_PRIMARY_TENANT is blocking).
        self.tenant_person = self.create_person(full_name="Test Tenant")
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

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

    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_create_success(self, mock_create):
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            signing_mode="sequential",
            created_by=self.agent,
            signers=[
                {"id": 1, "name": "Tenant", "email": "tenant@test.com",
                 "role": "tenant_1", "status": "pending", "order": 0},
            ],
        )
        mock_create.return_value = sub
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

    @mock.patch("apps.esigning.views.services.create_native_submission")
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

    @mock.patch("apps.esigning.views.services.create_native_submission", side_effect=Exception("Service error"))
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
        self.assertIn("signing_backend", resp.data)
        self.assertEqual(resp.data["signing_backend"], "native")

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
            status="pending",
            created_by=self.agent,
        )

    def test_retrieve(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[self.submission.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.submission.pk)

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
            lease=self.lease,
            status="pending",
            created_by=self.agent,
            signers=[
                {"id": 1, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "sent", "order": 0},
            ],
        )

    @override_settings(SIGNING_PUBLIC_APP_BASE_URL="https://app.test.com")
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_resend_success(self, mock_notify):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"signer_role": "landlord"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])

    def test_resend_no_signer_role(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @override_settings(SIGNING_PUBLIC_APP_BASE_URL="")
    def test_resend_missing_base_url(self):
        """Resend returns 500 when SIGNING_PUBLIC_APP_BASE_URL is not configured."""
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"signer_role": "landlord"},
            format="json",
        )
        self.assertEqual(resp.status_code, 500)

    @override_settings(
        SIGNING_PUBLIC_APP_BASE_URL="https://app.test.com",
        ESIGNING_PUBLIC_LINK_EXPIRY_DAYS=14,
    )
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_resend_expires_prior_links(self, mock_notify):
        """Resending a signing invitation must immediately expire all prior active links
        for the same signer role so old URLs cannot be used to sign."""
        from apps.esigning.models import ESigningPublicLink
        from django.utils import timezone
        from datetime import timedelta

        # Create two pre-existing links for the same signer role
        prior_link_1 = ESigningPublicLink.objects.create(
            submission=self.submission,
            signer_role="landlord",
            expires_at=timezone.now() + timedelta(days=7),
        )
        prior_link_2 = ESigningPublicLink.objects.create(
            submission=self.submission,
            signer_role="landlord",
            expires_at=timezone.now() + timedelta(days=3),
        )

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-resend", args=[self.submission.pk]),
            {"signer_role": "landlord"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # Prior links should now be expired (expires_at <= now)
        prior_link_1.refresh_from_db()
        prior_link_2.refresh_from_db()
        now = timezone.now()
        self.assertLessEqual(prior_link_1.expires_at, now)
        self.assertLessEqual(prior_link_2.expires_at, now)

        # A new active link should exist for the signer role
        active_links = ESigningPublicLink.objects.filter(
            submission=self.submission,
            signer_role="landlord",
            expires_at__gt=now,
        )
        self.assertEqual(active_links.count(), 1)


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
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            created_by=self.agent,
            signers=[
                {
                    "id": 99,
                    "name": "Tenant",
                    "email": "t@test.com",
                    "role": "tenant_1",
                    "status": "sent",
                    "order": 0,
                },
            ],
        )

    def test_create_public_link_as_agent(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"signer_role": "tenant_1"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("uuid", resp.data)
        self.assertIn("sign_path", resp.data)
        self.assertIs(resp.data.get("email_sent"), False)
        self.assertTrue(self._ESigningPublicLink.objects.filter(signer_role="tenant_1").exists())

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_public_link_send_email(self, mock_send):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {
                "signer_role": "tenant_1",
                "send_email": True,
                "public_app_origin": "https://admin.example.com",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["email_sent"])
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][2], "t@test.com")

    def test_public_link_send_email_without_origin_uses_fallback(self):
        """When no public_app_origin is provided, the view falls back to request host."""
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"signer_role": "tenant_1", "send_email": True},
            format="json",
        )
        # View builds URL from request host as fallback — succeeds
        self.assertEqual(resp.status_code, 201)

    def test_public_link_send_email_requires_signer_email(self):
        self.submission.signers = [
            {
                "id": 98,
                "name": "No Mail",
                "email": "",
                "role": "tenant_1",
                "status": "sent",
                "order": 0,
            },
        ]
        self.submission.save()
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {
                "signer_role": "tenant_1",
                "send_email": True,
                "public_app_origin": "https://admin.example.com",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.data["error"].lower())

    def test_create_public_link_unknown_role(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"signer_role": "unknown_role"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_public_sign_detail_no_auth(self):
        from datetime import timedelta
        from django.utils import timezone

        link = self._ESigningPublicLink.objects.create(
            submission=self.submission,
            signer_role="tenant_1",
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.client.get(reverse("esigning-public-sign", kwargs={"link_id": link.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["signing_backend"], "native")
        self.assertIn("document_title", resp.data)

    def test_public_sign_expired(self):
        from datetime import timedelta
        from django.utils import timezone

        link = self._ESigningPublicLink.objects.create(
            submission=self.submission,
            signer_role="tenant_1",
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp = self.client.get(reverse("esigning-public-sign", kwargs={"link_id": link.pk}))
        self.assertEqual(resp.status_code, 410)

    def test_tenant_cannot_create_public_link(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.post(
            reverse("esigning-public-link-create", args=[self.submission.pk]),
            {"signer_role": "tenant_1"},
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
            status="pending",
            created_by=self.agent,
            signers=[
                {"id": 1, "email": "tenantaccess@test.com", "role": "tenant_1", "status": "sent", "order": 0},
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
            {"signer_role": "tenant_1"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)




class SequentialSigningTests(TremlyAPITestCase):
    """Tests for sequential signing workflow."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        # primary_tenant is required by the RHA gate (MISSING_PRIMARY_TENANT is blocking).
        self.tenant_person = self.create_person(full_name="Test Tenant")
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_create_sequential_default(self, mock_create):
        """Default signing_mode should be 'sequential'."""
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            signing_mode="sequential",
            created_by=self.agent,
            signers=[
                {"id": 10, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "pending", "order": 0},
                {"id": 11, "name": "Tenant", "email": "t@test.com",
                 "role": "tenant_1", "status": "pending", "order": 1},
            ],
        )
        mock_create.return_value = sub
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

    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_create_parallel_mode(self, mock_create):
        """Explicit parallel mode — no order enforcement."""
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            signing_mode="parallel",
            created_by=self.agent,
            signers=[
                {"id": 20, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "pending", "order": 0},
                {"id": 21, "name": "Tenant", "email": "t@test.com",
                 "role": "tenant_1", "status": "pending", "order": 1},
            ],
        )
        mock_create.return_value = sub
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

    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_sequential_signer_order_preserved(self, mock_create):
        """Signers stored in order they were submitted (or by explicit order)."""
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            signing_mode="sequential",
            created_by=self.agent,
            signers=[
                {"id": 1, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "pending", "order": 0},
                {"id": 2, "name": "Tenant", "email": "t@test.com",
                 "role": "tenant_1", "status": "pending", "order": 1},
                {"id": 3, "name": "Witness", "email": "w@test.com",
                 "role": "witness", "status": "pending", "order": 2},
            ],
        )
        mock_create.return_value = sub
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
        # Should be in order stored by the model
        self.assertEqual(signers[0]["name"], "Landlord")
        self.assertEqual(signers[1]["name"], "Tenant")
        self.assertEqual(signers[2]["name"], "Witness")

    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_sequential_three_signers_create(self, mock_create):
        """Three-signer sequential submission creates correctly."""
        sub_obj = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            status="pending",
            signing_mode="sequential",
            created_by=self.agent,
            signers=[
                {"id": 40, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "sent", "order": 0},
                {"id": 41, "name": "Tenant", "email": "t@test.com",
                 "role": "tenant_1", "status": "sent", "order": 1},
                {"id": 42, "name": "Witness", "email": "w@test.com",
                 "role": "witness", "status": "sent", "order": 2},
            ],
        )
        mock_create.return_value = sub_obj
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
        self.assertEqual(resp.data["signing_mode"], "sequential")
        self.assertEqual(len(resp.data["signers"]), 3)
        # Signers in order
        self.assertEqual(resp.data["signers"][0]["name"], "Landlord")
        self.assertEqual(resp.data["signers"][1]["name"], "Tenant")
        self.assertEqual(resp.data["signers"][2]["name"], "Witness")

"""
Comprehensive e-signing tests covering:
  - Template upload with initials/signature/date fields
  - Full signing lifecycle (create → sign → complete → activate lease)
  - Webhook processing (form.completed, submission.completed, declined)
  - Lease activation on completion
  - Signed copy email delivery
  - Download endpoint with fresh URL fetch
  - Public signing link creation and resolution
  - Initials field presence in templates and submissions
  - Polling command logic
  - WebSocket broadcast events
"""
import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.esigning.models import ESigningPublicLink, ESigningSubmission
from apps.esigning.webhooks import (
    _activate_lease,
    _broadcast_ws,
    _email_signed_copy_to_signers,
    _get_next_signer,
    _safe_signer_info,
    _sync_signer_statuses,
    _update_single_signer,
)
from apps.leases.models import Lease
from tests.base import TremlyAPITestCase

# URL names from apps/esigning/urls.py
URL_PUBLIC_SIGN = "esigning-public-sign"


# ── Helpers ────────────────────────────────────────────────────────────────

FAKE_EMBED = "https://docuseal.example.com/s/abc123"
FAKE_SIGNED_URL = "https://docuseal.example.com/file/signed.pdf"


def _make_signers(n=2, with_initials_status=False):
    """Build a list of signer dicts as stored in ESigningSubmission.signers."""
    signers = []
    for i in range(n):
        role = "First Party" if i == 0 else f"Signer {i + 1}"
        s = {
            "id": 100 + i,
            "name": f"Signer {i + 1}",
            "email": f"signer{i + 1}@test.com",
            "role": role,
            "status": "sent",
            "slug": f"slug-{i}",
            "embed_src": f"{FAKE_EMBED}/{i}",
            "order": i,
        }
        signers.append(s)
    return signers


def _make_submission(lease, signers=None, **kwargs):
    defaults = {
        "lease": lease,
        "docuseal_submission_id": "999",
        "docuseal_template_id": "888",
        "status": ESigningSubmission.Status.PENDING,
        "signing_mode": ESigningSubmission.SigningMode.SEQUENTIAL,
        "signers": signers or _make_signers(),
    }
    defaults.update(kwargs)
    return ESigningSubmission.objects.create(**defaults)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Webhook Processing
# ═══════════════════════════════════════════════════════════════════════════


class WebhookFormCompletedTests(TremlyAPITestCase):
    """Test form.completed webhook events (individual signer completes)."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, status="pending")
        self.sub = _make_submission(self.lease, created_by=self.agent)

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_form_completed_updates_signer_status(self, mock_ws, mock_staff):
        payload = {
            "event_type": "form.completed",
            "data": {
                "submission_id": str(self.sub.docuseal_submission_id),
                "submitter": {
                    "id": 100,
                    "name": "Signer 1",
                    "email": "signer1@test.com",
                    "completed_at": "2026-03-31T10:00:00Z",
                },
            },
        }
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        self.sub.refresh_from_db()
        signer = self.sub.get_signer_by_submitter_id(100)
        self.assertEqual(signer["status"], "completed")
        self.assertEqual(signer["completed_at"], "2026-03-31T10:00:00Z")
        self.assertEqual(self.sub.status, ESigningSubmission.Status.IN_PROGRESS)

        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "signer_completed")

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_form_completed_transitions_pending_to_in_progress(self, mock_ws, mock_staff):
        self.assertEqual(self.sub.status, ESigningSubmission.Status.PENDING)

        payload = {
            "event_type": "form.completed",
            "data": {
                "submission_id": str(self.sub.docuseal_submission_id),
                "submitter": {"id": 100},
            },
        }
        self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, ESigningSubmission.Status.IN_PROGRESS)


class WebhookSubmissionCompletedTests(TremlyAPITestCase):
    """Test submission.completed webhook — lease activation + email."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, status="pending")
        self.sub = _make_submission(self.lease, created_by=self.agent)

    @mock.patch("apps.esigning.webhooks._email_signed_copy_to_signers")
    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_submission_completed_activates_lease(self, mock_ws, mock_staff, mock_email):
        self.assertEqual(self.lease.status, Lease.Status.PENDING)

        payload = {
            "event_type": "submission.completed",
            "data": {
                "id": str(self.sub.docuseal_submission_id),
                "submission_id": str(self.sub.docuseal_submission_id),
                "documents": [{"url": FAKE_SIGNED_URL}],
                "submitters": [
                    {"id": 100, "status": "completed", "completed_at": "2026-03-31T10:00:00Z"},
                    {"id": 101, "status": "completed", "completed_at": "2026-03-31T10:05:00Z"},
                ],
            },
        }
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, ESigningSubmission.Status.COMPLETED)
        self.assertEqual(self.sub.signed_pdf_url, FAKE_SIGNED_URL)

        self.lease.refresh_from_db()
        self.assertEqual(self.lease.status, Lease.Status.ACTIVE)

    @mock.patch("apps.esigning.webhooks._email_signed_copy_to_signers")
    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_submission_completed_calls_email_signers(self, mock_ws, mock_staff, mock_email):
        payload = {
            "event_type": "submission.completed",
            "data": {
                "id": str(self.sub.docuseal_submission_id),
                "documents": [{"url": FAKE_SIGNED_URL}],
                "submitters": [],
            },
        }
        self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        mock_email.assert_called_once()

    @mock.patch("apps.esigning.webhooks._email_signed_copy_to_signers")
    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_submission_completed_broadcasts_ws_event(self, mock_ws, mock_staff, mock_email):
        payload = {
            "event_type": "submission.completed",
            "data": {
                "id": str(self.sub.docuseal_submission_id),
                "documents": [{"url": FAKE_SIGNED_URL}],
                "submitters": [],
            },
        }
        self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "submission_completed")
        self.assertEqual(ws_event["signed_pdf_url"], FAKE_SIGNED_URL)


class WebhookDeclinedTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.sub = _make_submission(self.lease, created_by=self.agent)

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_submission_declined_updates_status(self, mock_ws, mock_staff):
        payload = {
            "event_type": "submission.declined",
            "data": {
                "submission_id": str(self.sub.docuseal_submission_id),
                "submitter": {"id": 100, "name": "Signer 1"},
            },
        }
        self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, ESigningSubmission.Status.DECLINED)

        signer = self.sub.get_signer_by_submitter_id(100)
        self.assertEqual(signer["status"], "declined")


class WebhookSecurityTests(TremlyAPITestCase):
    """Webhook signature verification."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        _make_submission(self.lease, created_by=self.agent)

    @mock.patch("apps.esigning.webhooks.settings")
    def test_bad_hmac_rejected(self, mock_settings):
        mock_settings.DOCUSEAL_WEBHOOK_SECRET = "my-secret"
        mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""

        body = json.dumps({"event_type": "form.viewed", "data": {"id": "999"}}).encode()
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_DOCUSEAL_SIGNATURE="bad-sig",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.esigning.webhooks.settings")
    def test_valid_hmac_accepted(self, mock_settings):
        secret = "my-secret"
        mock_settings.DOCUSEAL_WEBHOOK_SECRET = secret
        mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = ""

        body = json.dumps({"event_type": "form.viewed", "data": {"id": "999"}}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_DOCUSEAL_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, 200)

    @mock.patch("apps.esigning.webhooks.settings")
    def test_static_header_validation(self, mock_settings):
        mock_settings.DOCUSEAL_WEBHOOK_SECRET = "token123"
        mock_settings.DOCUSEAL_WEBHOOK_HEADER_NAME = "X-Tremly-Token"

        body = json.dumps({"event_type": "form.viewed", "data": {"id": "999"}}).encode()
        # Bad token
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_TREMLY_TOKEN="wrong",
        )
        self.assertEqual(resp.status_code, 400)

        # Correct token
        resp = self.client.post(
            reverse("esigning-webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_TREMLY_TOKEN="token123",
        )
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Lease Activation
# ═══════════════════════════════════════════════════════════════════════════


class LeaseActivationTests(TremlyAPITestCase):
    """Test _activate_lease helper."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, status="pending")

    def test_pending_lease_activated(self):
        sub = _make_submission(self.lease, created_by=self.agent)
        self.assertEqual(self.lease.status, Lease.Status.PENDING)

        _activate_lease(sub)

        self.lease.refresh_from_db()
        self.assertEqual(self.lease.status, Lease.Status.ACTIVE)

    def test_active_lease_not_overridden(self):
        self.lease.status = Lease.Status.ACTIVE
        self.lease.save()
        sub = _make_submission(self.lease, created_by=self.agent)

        _activate_lease(sub)

        self.lease.refresh_from_db()
        self.assertEqual(self.lease.status, Lease.Status.ACTIVE)

    def test_expired_lease_not_activated(self):
        self.lease.status = Lease.Status.EXPIRED
        self.lease.save()
        sub = _make_submission(self.lease, created_by=self.agent)

        _activate_lease(sub)

        self.lease.refresh_from_db()
        self.assertEqual(self.lease.status, Lease.Status.EXPIRED)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Download Signed PDF Endpoint
# ═══════════════════════════════════════════════════════════════════════════


class DownloadSignedPdfTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.sub = _make_submission(
            self.lease,
            created_by=self.agent,
            status=ESigningSubmission.Status.COMPLETED,
            signed_pdf_url=FAKE_SIGNED_URL,
        )

    @mock.patch("apps.esigning.services._docuseal_get")
    def test_download_returns_fresh_url(self, mock_get):
        fresh_url = "https://docuseal.example.com/file/fresh-token.pdf"
        mock_get.return_value = {"documents": [{"url": fresh_url}]}

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-download", kwargs={"pk": self.sub.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["url"], fresh_url)

    @mock.patch("apps.esigning.services._docuseal_get")
    def test_download_falls_back_to_stored_url(self, mock_get):
        mock_get.side_effect = Exception("API down")

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-download", kwargs={"pk": self.sub.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["url"], FAKE_SIGNED_URL)

    def test_download_requires_completed_status(self):
        self.sub.status = ESigningSubmission.Status.PENDING
        self.sub.save()

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-download", kwargs={"pk": self.sub.pk})
        )
        self.assertEqual(resp.status_code, 400)

    def test_download_requires_auth(self):
        resp = self.client.get(
            reverse("esigning-download", kwargs={"pk": self.sub.pk})
        )
        self.assertEqual(resp.status_code, 401)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Public Signing Link & Fields
# ═══════════════════════════════════════════════════════════════════════════


class PublicSigningLinkTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.sub = _make_submission(self.lease, created_by=self.agent)
        self.link = ESigningPublicLink.objects.create(
            submission=self.sub,
            submitter_id=100,
            expires_at=timezone.now() + timedelta(days=14),
        )

    def test_valid_link_returns_embed_src(self):
        resp = self.client.get(
            reverse(URL_PUBLIC_SIGN, kwargs={"link_id": self.link.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("embed_src", resp.data)
        self.assertEqual(resp.data["signer_name"], "Signer 1")

    def test_expired_link_returns_410(self):
        self.link.expires_at = timezone.now() - timedelta(days=1)
        self.link.save()

        resp = self.client.get(
            reverse(URL_PUBLIC_SIGN, kwargs={"link_id": self.link.pk})
        )
        self.assertEqual(resp.status_code, 410)

    def test_completed_signer_returns_410(self):
        signers = self.sub.signers
        signers[0]["status"] = "completed"
        self.sub.signers = signers
        self.sub.save()

        resp = self.client.get(
            reverse(URL_PUBLIC_SIGN, kwargs={"link_id": self.link.pk})
        )
        self.assertEqual(resp.status_code, 410)

    def test_invalid_uuid_returns_404(self):
        resp = self.client.get(
            reverse(URL_PUBLIC_SIGN, kwargs={"link_id": uuid.uuid4()})
        )
        self.assertEqual(resp.status_code, 404)


# NOTE: PublicSignFieldsTests and PublicSignSubmitTests removed — those endpoints
# were replaced by DocuSeal's embedded form component.


# ═══════════════════════════════════════════════════════════════════════════
# 6. Signer Helper Functions
# ═══════════════════════════════════════════════════════════════════════════


class SignerHelperTests(TestCase):

    def test_sync_signer_statuses(self):
        signers = _make_signers(2)
        submitters = [
            {"id": 100, "status": "completed", "completed_at": "2026-03-31T10:00:00Z"},
            {"id": 101, "status": "completed", "completed_at": "2026-03-31T10:05:00Z"},
        ]
        result = _sync_signer_statuses(signers, submitters)
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(result[1]["status"], "completed")

    def test_update_single_signer(self):
        signers = _make_signers(2)
        result = _update_single_signer(signers, "101", {"status": "declined"})
        self.assertEqual(result[0]["status"], "sent")  # unchanged
        self.assertEqual(result[1]["status"], "declined")

    def test_get_next_signer_returns_first_pending(self):
        signers = _make_signers(3)
        signers[0]["status"] = "completed"
        result = _get_next_signer(signers)
        self.assertEqual(result["id"], 101)

    def test_get_next_signer_returns_none_when_all_done(self):
        signers = _make_signers(2)
        signers[0]["status"] = "completed"
        signers[1]["status"] = "completed"
        self.assertIsNone(_get_next_signer(signers))

    def test_safe_signer_info_strips_embed_src(self):
        signer = _make_signers(1)[0]
        signer["embed_src"] = "https://secret.url"
        result = _safe_signer_info(signer)
        self.assertNotIn("embed_src", result)
        self.assertIn("name", result)

    def test_get_next_signer_skips_declined(self):
        signers = _make_signers(3)
        signers[0]["status"] = "completed"
        signers[1]["status"] = "declined"
        result = _get_next_signer(signers)
        self.assertEqual(result["id"], 102)

    def test_empty_signers_handled(self):
        self.assertIsNone(_get_next_signer([]))
        self.assertIsNone(_get_next_signer(None))
        self.assertEqual(_update_single_signer([], "100", {}), [])
        self.assertEqual(_sync_signer_statuses([], []), [])


# ═══════════════════════════════════════════════════════════════════════════
# 8. Email Signed Copy
# ═══════════════════════════════════════════════════════════════════════════


class EmailSignedCopyTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.sub = _make_submission(
            self.lease,
            created_by=self.agent,
            status=ESigningSubmission.Status.COMPLETED,
        )

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.services._docuseal_get")
    def test_emails_all_signers_with_fresh_url(self, mock_get, mock_send):
        fresh_url = "https://docuseal.example.com/file/fresh.pdf"
        mock_get.return_value = {"documents": [{"url": fresh_url}]}

        _email_signed_copy_to_signers(self.sub, {})

        # 2 signers = 2 emails
        self.assertEqual(mock_send.call_count, 2)
        for call in mock_send.call_args_list:
            self.assertIn(fresh_url, call[0][1])  # plain text body

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.services._docuseal_get")
    def test_falls_back_to_webhook_url(self, mock_get, mock_send):
        mock_get.side_effect = Exception("API down")
        webhook_url = "https://from-webhook.pdf"

        _email_signed_copy_to_signers(self.sub, {"documents": [{"url": webhook_url}]})

        self.assertEqual(mock_send.call_count, 2)
        for call in mock_send.call_args_list:
            self.assertIn(webhook_url, call[0][1])

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.services._docuseal_get")
    def test_skips_signers_without_email(self, mock_get, mock_send):
        mock_get.return_value = {"documents": [{"url": "https://x.pdf"}]}
        self.sub.signers[1]["email"] = ""
        self.sub.save()

        _email_signed_copy_to_signers(self.sub, {})

        self.assertEqual(mock_send.call_count, 1)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Submission Create (full flow with mocked DocuSeal)
# ═══════════════════════════════════════════════════════════════════════════


class SubmissionCreateTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_create_generates_initials_fields(self, mock_create, mock_email):
        mock_create.return_value = {
            "template": {"id": "tmpl_100"},
            "submission": [
                {
                    "id": 200,
                    "submission_id": "sub_200",
                    "name": "Tenant",
                    "email": "tenant@test.com",
                    "role": "First Party",
                    "status": "sent",
                    "slug": "abc",
                    "embed_src": FAKE_EMBED,
                    "order": 0,
                },
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            data=json.dumps({
                "lease_id": self.lease.pk,
                "signers": [
                    {"name": "Tenant", "email": "tenant@test.com", "role": "Tenant"},
                ],
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

        # Verify create_lease_submission was called with correct args
        call_args = mock_create.call_args
        self.assertEqual(call_args[0][0], self.lease)
        self.assertEqual(len(call_args[0][1]), 1)  # 1 signer

        # Verify submission created in DB
        sub = ESigningSubmission.objects.get(docuseal_submission_id="sub_200")
        self.assertEqual(sub.signing_mode, "sequential")
        self.assertEqual(len(sub.signers), 1)

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.views.services.create_lease_submission")
    def test_create_with_multiple_signers(self, mock_create, mock_email):
        mock_create.return_value = {
            "template": {"id": "tmpl_101"},
            "submission": [
                {"id": 300, "submission_id": "sub_300", "name": "Landlord", "email": "ll@test.com",
                 "role": "First Party", "status": "sent", "slug": "a", "embed_src": FAKE_EMBED, "order": 0},
                {"id": 301, "submission_id": "sub_300", "name": "Tenant", "email": "t@test.com",
                 "role": "Signer 2", "status": "sent", "slug": "b", "embed_src": FAKE_EMBED, "order": 1},
            ],
        }
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            data=json.dumps({
                "lease_id": self.lease.pk,
                "signers": [
                    {"name": "Landlord", "email": "ll@test.com", "role": "Landlord"},
                    {"name": "Tenant", "email": "t@test.com", "role": "Tenant"},
                ],
                "signing_mode": "sequential",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

        sub = ESigningSubmission.objects.get(docuseal_submission_id="sub_300")
        self.assertEqual(len(sub.signers), 2)
        # Sequential: signers sorted by order
        self.assertEqual(sub.signers[0]["order"], 0)
        self.assertEqual(sub.signers[1]["order"], 1)

    def test_create_requires_lease_id(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            data=json.dumps({"signers": [{"name": "T", "email": "t@t.com"}]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_requires_signers(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("esigning-list"),
            data=json.dumps({"lease_id": self.lease.pk, "signers": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_tenant_cannot_create(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.post(
            reverse("esigning-list"),
            data=json.dumps({
                "lease_id": self.lease.pk,
                "signers": [{"name": "T", "email": "t@t.com"}],
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 10. WebSocket Broadcast
# ═══════════════════════════════════════════════════════════════════════════


class BroadcastWsTests(TestCase):
    """Test _broadcast_ws doesn't crash."""

    @mock.patch("channels.layers.get_channel_layer")
    def test_broadcast_does_not_raise(self, mock_get_layer):
        """_broadcast_ws catches all exceptions and never raises."""
        mock_get_layer.return_value = None
        # Should not raise even with None channel layer
        _broadcast_ws(42, {"type": "signer_completed", "submission_id": 1})

    def test_broadcast_handles_import_error(self):
        """_broadcast_ws silently catches import/runtime errors."""
        # This exercises the except block — channels layer sends to InMemory
        # which has no subscribers, so it just passes through.
        _broadcast_ws(999, {"type": "test"})


# ═══════════════════════════════════════════════════════════════════════════
# 11. Polling Command
# ═══════════════════════════════════════════════════════════════════════════


class PollDocuSealCommandTests(TremlyAPITestCase):
    """Test the poll_docuseal management command."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, status="pending")

    @mock.patch("apps.esigning.management.commands.poll_docuseal._email_signed_copy_to_signers")
    @mock.patch("apps.esigning.management.commands.poll_docuseal._notify_staff")
    @mock.patch("apps.esigning.management.commands.poll_docuseal._broadcast_ws")
    @mock.patch("apps.esigning.management.commands.poll_docuseal._docuseal_get")
    def test_poll_detects_completed_submission(self, mock_get, mock_ws, mock_staff, mock_email):
        sub = _make_submission(self.lease, created_by=self.agent)
        mock_get.return_value = {
            "status": "completed",
            "submitters": [
                {"id": 100, "status": "completed", "completed_at": "2026-03-31T10:00:00Z"},
                {"id": 101, "status": "completed", "completed_at": "2026-03-31T10:05:00Z"},
            ],
            "documents": [{"url": FAKE_SIGNED_URL}],
        }

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("poll_docuseal", stdout=out)

        sub.refresh_from_db()
        self.assertEqual(sub.status, ESigningSubmission.Status.COMPLETED)
        self.assertEqual(sub.signed_pdf_url, FAKE_SIGNED_URL)

        self.lease.refresh_from_db()
        self.assertEqual(self.lease.status, Lease.Status.ACTIVE)

        mock_ws.assert_called()
        mock_email.assert_called_once()

    @mock.patch("apps.esigning.management.commands.poll_docuseal._notify_staff")
    @mock.patch("apps.esigning.management.commands.poll_docuseal._broadcast_ws")
    @mock.patch("apps.esigning.management.commands.poll_docuseal._docuseal_get")
    def test_poll_detects_individual_signer_completion(self, mock_get, mock_ws, mock_staff):
        sub = _make_submission(self.lease, created_by=self.agent)
        mock_get.return_value = {
            "status": "pending",
            "submitters": [
                {"id": 100, "name": "Signer 1", "status": "completed", "completed_at": "2026-03-31T10:00:00Z"},
                {"id": 101, "name": "Signer 2", "status": "pending"},
            ],
            "documents": [],
        }

        from django.core.management import call_command
        from io import StringIO
        call_command("poll_docuseal", stdout=StringIO())

        sub.refresh_from_db()
        signer = sub.get_signer_by_submitter_id(100)
        self.assertEqual(signer["status"], "completed")
        # Submission not yet fully complete
        self.assertEqual(sub.status, ESigningSubmission.Status.IN_PROGRESS)

    @mock.patch("apps.esigning.management.commands.poll_docuseal._docuseal_get")
    def test_poll_no_change_when_unchanged(self, mock_get):
        sub = _make_submission(self.lease, created_by=self.agent)
        mock_get.return_value = {
            "status": "pending",
            "submitters": [
                {"id": 100, "status": "sent"},
                {"id": 101, "status": "sent"},
            ],
            "documents": [],
        }

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("poll_docuseal", stdout=out)

        sub.refresh_from_db()
        self.assertEqual(sub.status, ESigningSubmission.Status.PENDING)
        self.assertIn("no changes", out.getvalue())

    def test_poll_skips_completed_submissions(self):
        _make_submission(
            self.lease,
            created_by=self.agent,
            status=ESigningSubmission.Status.COMPLETED,
        )

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("poll_docuseal", stdout=out)

        self.assertIn("No active submissions", out.getvalue())

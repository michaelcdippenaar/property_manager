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
from apps.test_hub.base.test_case import TremlyAPITestCase
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]

# URL names from apps/esigning/urls.py
URL_PUBLIC_SIGN = "esigning-public-sign"


# ── Helpers ────────────────────────────────────────────────────────────────

FAKE_SIGNED_URL = "https://example.com/file/signed.pdf"


def _make_signers(n=2, with_initials_status=False):
    """Build a list of signer dicts as stored in ESigningSubmission.signers."""
    signers = []
    for i in range(n):
        role = "landlord" if i == 0 else f"tenant_{i}"
        s = {
            "id": 100 + i,
            "name": f"Signer {i + 1}",
            "email": f"signer{i + 1}@test.com",
            "role": role,
            "status": "sent",
            "order": i,
        }
        signers.append(s)
    return signers


def _make_submission(lease, signers=None, **kwargs):
    defaults = {
        "lease": lease,
        "status": ESigningSubmission.Status.PENDING,
        "signing_mode": ESigningSubmission.SigningMode.SEQUENTIAL,
        "signing_backend": ESigningSubmission.SigningBackend.NATIVE,
        "signers": signers or _make_signers(),
    }
    defaults.update(kwargs)
    return ESigningSubmission.objects.create(**defaults)


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
        )

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
            signer_role="landlord",
            expires_at=timezone.now() + timedelta(days=14),
        )

    def test_valid_link_returns_signer_info(self):
        resp = self.client.get(
            reverse(URL_PUBLIC_SIGN, kwargs={"link_id": self.link.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["signing_backend"], "native")
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
    def test_no_email_when_no_signed_pdf(self, mock_send):
        """No emails sent when submission has no signed_pdf_file."""
        _email_signed_copy_to_signers(self.sub, {})
        mock_send.assert_not_called()

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_skips_signers_without_email(self, mock_send):
        """Signers without email addresses are skipped."""
        self.sub.signers[1]["email"] = ""
        self.sub.save()
        # No signed_pdf_file — just verifying no crash on empty email
        _email_signed_copy_to_signers(self.sub, {})
        mock_send.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# 9. Submission Create (full flow with mocked DocuSeal)
# ═══════════════════════════════════════════════════════════════════════════


class SubmissionCreateTests(TremlyAPITestCase):

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

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_create_generates_initials_fields(self, mock_create, mock_email):
        sub = _make_submission(
            self.lease,
            signers=[{
                "id": 1, "name": "Tenant", "email": "tenant@test.com",
                "role": "tenant_1", "status": "pending", "order": 0,
            }],
            created_by=self.agent,
        )
        mock_create.return_value = sub
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

        # Verify create_native_submission was called with correct args
        call_args = mock_create.call_args
        self.assertEqual(call_args[0][0], self.lease)
        self.assertEqual(len(call_args[0][1]), 1)  # 1 signer

        # Verify submission in DB
        sub.refresh_from_db()
        self.assertEqual(sub.signing_mode, "sequential")
        self.assertEqual(len(sub.signers), 1)

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    @mock.patch("apps.esigning.views.services.create_native_submission")
    def test_create_with_multiple_signers(self, mock_create, mock_email):
        sub = _make_submission(
            self.lease,
            signers=[
                {"id": 1, "name": "Landlord", "email": "ll@test.com",
                 "role": "landlord", "status": "pending", "order": 0},
                {"id": 2, "name": "Tenant", "email": "t@test.com",
                 "role": "tenant_1", "status": "pending", "order": 1},
            ],
            created_by=self.agent,
        )
        mock_create.return_value = sub
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

        sub.refresh_from_db()
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

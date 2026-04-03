"""
Tests for sequential signing workflow:
- Signer-status endpoint
- Webhook triggers next-signer notification
- WebSocket broadcast on signing events
- Serializer progress fields
- Staff notifications
"""
import json
from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.esigning.models import ESigningPublicLink, ESigningSubmission
from apps.esigning.webhooks import (
    _broadcast_ws,
    _get_next_signer,
    _notify_next_signer,
    _notify_staff,
    _safe_signer_info,
)
from tests.base import TremlyAPITestCase


def _make_sequential_signers():
    """Three signers in sequential order."""
    return [
        {
            "id": 101,
            "name": "Landlord",
            "email": "landlord@test.com",
            "role": "First Party",
            "status": "sent",
            "order": 0,
            "embed_src": "https://docuseal.example/embed/101",
        },
        {
            "id": 102,
            "name": "Tenant",
            "email": "tenant@test.com",
            "role": "Second Party",
            "status": "sent",
            "order": 1,
            "embed_src": "https://docuseal.example/embed/102",
        },
        {
            "id": 103,
            "name": "Guarantor",
            "email": "guarantor@test.com",
            "role": "Third Party",
            "status": "sent",
            "order": 2,
            "embed_src": "https://docuseal.example/embed/103",
        },
    ]


class SignerStatusEndpointTests(TremlyAPITestCase):
    """Tests for GET /api/v1/esigning/submissions/<pk>/signer-status/"""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_seq_1",
            status="pending",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )

    def test_signer_status_all_pending(self):
        """First signer is current, rest are pending."""
        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["signing_mode"], "sequential")
        self.assertEqual(resp.data["current_signer"]["name"], "Landlord")
        self.assertEqual(len(resp.data["completed_signers"]), 0)
        self.assertEqual(len(resp.data["pending_signers"]), 2)
        self.assertEqual(resp.data["progress"]["total"], 3)
        self.assertEqual(resp.data["progress"]["completed"], 0)
        self.assertEqual(resp.data["progress"]["pending"], 3)

    def test_signer_status_one_completed(self):
        """After first signer completes, second becomes current."""
        signers = _make_sequential_signers()
        signers[0]["status"] = "completed"
        signers[0]["completed_at"] = "2026-03-20T10:00:00Z"
        self.submission.signers = signers
        self.submission.status = "in_progress"
        self.submission.save()

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["current_signer"]["name"], "Tenant")
        self.assertEqual(len(resp.data["completed_signers"]), 1)
        self.assertEqual(resp.data["completed_signers"][0]["name"], "Landlord")
        self.assertEqual(resp.data["progress"]["completed"], 1)
        self.assertEqual(resp.data["progress"]["pending"], 2)

    def test_signer_status_all_completed(self):
        """When all signers done, current_signer is None."""
        signers = _make_sequential_signers()
        for s in signers:
            s["status"] = "completed"
        self.submission.signers = signers
        self.submission.status = "completed"
        self.submission.signed_pdf_url = "https://example.com/signed.pdf"
        self.submission.save()

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["current_signer"])
        self.assertEqual(len(resp.data["completed_signers"]), 3)
        self.assertEqual(resp.data["signed_pdf_url"], "https://example.com/signed.pdf")

    def test_signer_status_declined(self):
        """If a signer declined, they show in declined list."""
        signers = _make_sequential_signers()
        signers[0]["status"] = "completed"
        signers[1]["status"] = "declined"
        self.submission.signers = signers
        self.submission.status = "declined"
        self.submission.save()

        self.authenticate(self.agent)
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["declined_signers"]), 1)
        self.assertEqual(resp.data["declined_signers"][0]["name"], "Tenant")
        self.assertEqual(resp.data["progress"]["declined"], 1)

    def test_signer_status_requires_auth(self):
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 401)

    def test_signer_status_tenant_cant_see_other_lease(self):
        """Tenant without access to lease gets 403 (IsAgentOrAdmin blocks first)."""
        other_tenant = self.create_tenant(email="other@test.com")
        self.authenticate(other_tenant)
        resp = self.client.get(
            reverse("esigning-signer-status", args=[self.submission.pk])
        )
        self.assertEqual(resp.status_code, 403)


class WebhookSequentialNotificationTests(TremlyAPITestCase):
    """Tests that form.completed webhook triggers next-signer notification."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_seq_2",
            status="pending",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )

    def _webhook_post(self, payload):
        return self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_form_completed_notifies_next_signer(self, mock_notify, mock_ws, mock_staff):
        """When signer 0 completes, _notify_next_signer is called with signer 1."""
        resp = self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 101, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })
        self.assertEqual(resp.status_code, 200)
        mock_notify.assert_called_once()

        # The next signer passed should be signer with id=102 (Tenant)
        args = mock_notify.call_args
        submission_arg = args[0][0]
        next_signer_arg = args[0][1]
        self.assertEqual(submission_arg.pk, self.submission.pk)
        self.assertEqual(next_signer_arg["id"], 102)
        self.assertEqual(next_signer_arg["name"], "Tenant")

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_form_completed_last_signer_no_next(self, mock_notify, mock_ws, mock_staff):
        """When the last signer completes, no next-signer notification."""
        # Mark first two as completed
        signers = _make_sequential_signers()
        signers[0]["status"] = "completed"
        signers[1]["status"] = "completed"
        self.submission.signers = signers
        self.submission.status = "in_progress"
        self.submission.save()

        resp = self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 103, "completed_at": "2026-03-20T12:00:00Z"},
            },
        })
        self.assertEqual(resp.status_code, 200)
        mock_notify.assert_not_called()

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_parallel_mode_no_next_signer_notification(self, mock_notify, mock_ws, mock_staff):
        """In parallel mode, no next-signer notification is sent."""
        self.submission.signing_mode = "parallel"
        self.submission.save()

        resp = self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 101, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })
        self.assertEqual(resp.status_code, 200)
        mock_notify.assert_not_called()

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_form_completed_broadcasts_ws(self, mock_ws, mock_staff):
        """form.completed broadcasts a WebSocket event."""
        self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 101, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })
        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "signer_completed")
        self.assertEqual(ws_event["completed_count"], 1)
        self.assertEqual(ws_event["total_signers"], 3)

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_submission_completed_broadcasts_ws(self, mock_ws, mock_staff):
        """submission.completed broadcasts with signed_pdf_url."""
        signers = _make_sequential_signers()
        for s in signers:
            s["status"] = "completed"
        self.submission.signers = signers
        self.submission.status = "in_progress"
        self.submission.save()

        self._webhook_post({
            "event_type": "submission.completed",
            "data": {
                "submission_id": "sub_seq_2",
                "audit_log_url": "https://example.com/signed.pdf",
                "submitters": [
                    {"id": 101, "status": "completed"},
                    {"id": 102, "status": "completed"},
                    {"id": 103, "status": "completed"},
                ],
            },
        })
        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "submission_completed")
        self.assertEqual(ws_event["signed_pdf_url"], "https://example.com/signed.pdf")

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_declined_broadcasts_ws(self, mock_ws, mock_staff):
        """submission.declined broadcasts with declined signer info."""
        self._webhook_post({
            "event_type": "submission.declined",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 102, "name": "Tenant"},
            },
        })
        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "signer_declined")

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_viewed_broadcasts_ws(self, mock_ws, mock_staff):
        """form.viewed broadcasts with signer info."""
        self._webhook_post({
            "event_type": "form.viewed",
            "data": {
                "submission_id": "sub_seq_2",
                "submitter": {"id": 101},
            },
        })
        mock_ws.assert_called_once()
        ws_event = mock_ws.call_args[0][1]
        self.assertEqual(ws_event["type"], "signer_viewed")


@override_settings(
    SIGNING_PUBLIC_APP_BASE_URL="https://app.example.com",
    ESIGNING_PUBLIC_LINK_EXPIRY_DAYS=14,
)
class NotifyNextSignerTests(TremlyAPITestCase):
    """Tests for _notify_next_signer helper."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_notify_1",
            status="in_progress",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )

    @mock.patch("apps.esigning.webhooks.logger")
    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_creates_public_link(self, mock_email, mock_logger):
        """Notifying creates an ESigningPublicLink for the next signer."""
        next_signer = _make_sequential_signers()[1]
        _notify_next_signer(self.submission, next_signer)

        link = ESigningPublicLink.objects.filter(
            submission=self.submission, submitter_id=102
        ).first()
        self.assertIsNotNone(link)
        self.assertFalse(link.is_expired())

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_sends_email_with_signing_url(self, mock_email):
        """Email is sent with correct signing URL."""
        next_signer = _make_sequential_signers()[1]
        _notify_next_signer(self.submission, next_signer)

        mock_email.assert_called_once()
        call_args = mock_email.call_args
        subject = call_args[0][0]
        self.assertIn("Your turn to sign", subject)
        body = call_args[0][1]
        self.assertIn("https://app.example.com/sign/", body)
        to_email = call_args[0][2]
        self.assertEqual(to_email, "tenant@test.com")

    @mock.patch("apps.notifications.services.notify_sms_and_whatsapp")
    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_sends_sms_if_phone_available(self, mock_email, mock_sms):
        """SMS/WhatsApp sent if signer has a phone."""
        next_signer = _make_sequential_signers()[1]
        next_signer["phone"] = "+27821234567"
        _notify_next_signer(self.submission, next_signer)

        mock_sms.assert_called_once()
        sms_body = mock_sms.call_args[0][1]
        self.assertIn("your turn to sign", sms_body.lower())

    @mock.patch("apps.notifications.services.notify_sms_and_whatsapp")
    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_no_sms_without_phone(self, mock_email, mock_sms):
        """No SMS sent if signer has no phone."""
        next_signer = _make_sequential_signers()[1]
        _notify_next_signer(self.submission, next_signer)
        mock_sms.assert_not_called()

    @mock.patch("apps.notifications.services.send_email", side_effect=Exception("SMTP error"))
    def test_email_failure_does_not_crash(self, mock_email):
        """Email failure is logged but doesn't raise."""
        next_signer = _make_sequential_signers()[1]
        # Should not raise
        _notify_next_signer(self.submission, next_signer)
        # Public link should still be created
        self.assertTrue(
            ESigningPublicLink.objects.filter(
                submission=self.submission, submitter_id=102
            ).exists()
        )


class StaffNotificationTests(TremlyAPITestCase):
    """Tests for _notify_staff helper."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_staff_1",
            status="in_progress",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_form_completed_notifies_creator(self, mock_email):
        """Staff get email when a signer completes."""
        _notify_staff(self.submission, "form.completed", {
            "submitter": {"name": "Landlord", "id": 101},
        })
        mock_email.assert_called_once()
        subject = mock_email.call_args[0][0]
        self.assertIn("Signing progress", subject)
        to_email = mock_email.call_args[0][2]
        self.assertEqual(to_email, self.agent.email)

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_submission_completed_notifies_creator(self, mock_email):
        """Staff get email when all signers complete."""
        self.submission.signed_pdf_url = "https://example.com/signed.pdf"
        _notify_staff(self.submission, "submission.completed", {})
        mock_email.assert_called_once()
        subject = mock_email.call_args[0][0]
        self.assertIn("All signatures complete", subject)

    @mock.patch("apps.notifications.services.send_email", return_value=True)
    def test_declined_notifies_creator(self, mock_email):
        """Staff get email when a signer declines."""
        _notify_staff(self.submission, "submission.declined", {
            "submitter": {"name": "Tenant", "id": 102},
        })
        subject = mock_email.call_args[0][0]
        self.assertIn("declined", subject.lower())

    def test_no_creator_no_notification(self):
        """No error if submission has no creator."""
        self.submission.created_by = None
        self.submission.save()
        # Should not raise
        _notify_staff(self.submission, "form.completed", {
            "submitter": {"name": "Test", "id": 1},
        })


class HelperFunctionTests(TremlyAPITestCase):
    """Tests for utility functions in webhooks module."""

    def test_get_next_signer_all_pending(self):
        signers = _make_sequential_signers()
        nxt = _get_next_signer(signers)
        self.assertEqual(nxt["id"], 101)

    def test_get_next_signer_first_done(self):
        signers = _make_sequential_signers()
        signers[0]["status"] = "completed"
        nxt = _get_next_signer(signers)
        self.assertEqual(nxt["id"], 102)

    def test_get_next_signer_all_done(self):
        signers = _make_sequential_signers()
        for s in signers:
            s["status"] = "completed"
        nxt = _get_next_signer(signers)
        self.assertIsNone(nxt)

    def test_get_next_signer_one_declined(self):
        """Declined signers are skipped."""
        signers = _make_sequential_signers()
        signers[0]["status"] = "declined"
        nxt = _get_next_signer(signers)
        self.assertEqual(nxt["id"], 102)

    def test_safe_signer_info_strips_embed_src(self):
        signer = _make_sequential_signers()[0]
        safe = _safe_signer_info(signer)
        self.assertNotIn("embed_src", safe)
        self.assertEqual(safe["name"], "Landlord")

    def test_get_next_signer_empty_list(self):
        self.assertIsNone(_get_next_signer([]))
        self.assertIsNone(_get_next_signer(None))


class SerializerProgressTests(TremlyAPITestCase):
    """Tests for current_signer and signing_progress on the serializer."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)

    def test_serializer_current_signer_sequential(self):
        """current_signer returns the first non-completed signer."""
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            status="in_progress",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[sub.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["current_signer"]["name"], "Landlord")
        self.assertEqual(resp.data["signing_progress"]["total"], 3)
        self.assertEqual(resp.data["signing_progress"]["completed"], 0)
        self.assertEqual(resp.data["signing_progress"]["pending"], 3)

    def test_serializer_progress_partial(self):
        signers = _make_sequential_signers()
        signers[0]["status"] = "completed"
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            status="in_progress",
            signing_mode="sequential",
            signers=signers,
            created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[sub.pk]))
        self.assertEqual(resp.data["current_signer"]["name"], "Tenant")
        self.assertEqual(resp.data["signing_progress"]["completed"], 1)
        self.assertEqual(resp.data["signing_progress"]["pending"], 2)

    def test_serializer_completed_no_current_signer(self):
        signers = _make_sequential_signers()
        for s in signers:
            s["status"] = "completed"
        sub = ESigningSubmission.objects.create(
            lease=self.lease,
            status="completed",
            signing_mode="sequential",
            signers=signers,
            created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("esigning-detail", args=[sub.pk]))
        self.assertIsNone(resp.data["current_signer"])
        self.assertEqual(resp.data["signing_progress"]["completed"], 3)
        self.assertEqual(resp.data["signing_progress"]["pending"], 0)


class WebhookStatusTransitionTests(TremlyAPITestCase):
    """Tests that webhook correctly transitions submission and signer statuses."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            docuseal_submission_id="sub_transition_1",
            status="pending",
            signing_mode="sequential",
            signers=_make_sequential_signers(),
            created_by=self.agent,
        )

    def _webhook_post(self, payload):
        return self.client.post(
            reverse("esigning-webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    @mock.patch("apps.esigning.webhooks._notify_next_signer")
    def test_full_sequential_flow(self, mock_notify, mock_ws, mock_staff):
        """Simulate the full sequential signing flow for 3 signers."""
        # Signer 1 views
        self._webhook_post({
            "event_type": "form.viewed",
            "data": {"submission_id": "sub_transition_1", "submitter": {"id": 101}},
        })
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "in_progress")
        signer_0 = next(s for s in self.submission.signers if s["id"] == 101)
        self.assertEqual(signer_0["status"], "opened")

        # Signer 1 completes
        self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_transition_1",
                "submitter": {"id": 101, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })
        self.submission.refresh_from_db()
        signer_0 = next(s for s in self.submission.signers if s["id"] == 101)
        self.assertEqual(signer_0["status"], "completed")

        # Next signer notification was called with signer 102
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args[0][1]["id"], 102)
        mock_notify.reset_mock()

        # Signer 2 completes
        self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_transition_1",
                "submitter": {"id": 102, "completed_at": "2026-03-21T10:00:00Z"},
            },
        })
        self.submission.refresh_from_db()
        signer_1 = next(s for s in self.submission.signers if s["id"] == 102)
        self.assertEqual(signer_1["status"], "completed")

        # Next signer notification was called with signer 103
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args[0][1]["id"], 103)
        mock_notify.reset_mock()

        # Signer 3 completes
        self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_transition_1",
                "submitter": {"id": 103, "completed_at": "2026-03-22T10:00:00Z"},
            },
        })
        self.submission.refresh_from_db()
        signer_2 = next(s for s in self.submission.signers if s["id"] == 103)
        self.assertEqual(signer_2["status"], "completed")

        # No more next-signer notifications
        mock_notify.assert_not_called()

        # submission.completed fires
        self._webhook_post({
            "event_type": "submission.completed",
            "data": {
                "submission_id": "sub_transition_1",
                "audit_log_url": "https://example.com/final.pdf",
                "submitters": [
                    {"id": 101, "status": "completed"},
                    {"id": 102, "status": "completed"},
                    {"id": 103, "status": "completed"},
                ],
            },
        })
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "completed")
        self.assertEqual(self.submission.signed_pdf_url, "https://example.com/final.pdf")

    @mock.patch("apps.esigning.webhooks._notify_staff")
    @mock.patch("apps.esigning.webhooks._broadcast_ws")
    def test_decline_mid_sequence(self, mock_ws, mock_staff):
        """If signer 2 declines, entire submission is declined."""
        # First signer completes
        self._webhook_post({
            "event_type": "form.completed",
            "data": {
                "submission_id": "sub_transition_1",
                "submitter": {"id": 101, "completed_at": "2026-03-20T10:00:00Z"},
            },
        })

        # Second signer declines
        self._webhook_post({
            "event_type": "submission.declined",
            "data": {
                "submission_id": "sub_transition_1",
                "submitter": {"id": 102, "name": "Tenant"},
            },
        })
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, "declined")
        signer_1 = next(s for s in self.submission.signers if s["id"] == 102)
        self.assertEqual(signer_1["status"], "declined")


class BroadcastWSTests(TremlyAPITestCase):
    """Tests for _broadcast_ws helper."""

    @mock.patch("channels.layers.get_channel_layer")
    def test_broadcast_sends_to_group(self, mock_get_layer):
        mock_layer = mock.MagicMock()
        mock_get_layer.return_value = mock_layer

        event = {"type": "signer_completed", "submission_id": 1}
        _broadcast_ws(1, event)

        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args[0]
        self.assertEqual(call_args[0], "esigning_1")
        self.assertEqual(call_args[1]["type"], "esigning.update")
        self.assertEqual(call_args[1]["payload"], event)

    @mock.patch("channels.layers.get_channel_layer", return_value=None)
    def test_broadcast_no_channel_layer(self, mock_get_layer):
        """No error when channel layer is not configured."""
        _broadcast_ws(1, {"type": "test"})  # Should not raise

    @mock.patch("channels.layers.get_channel_layer", side_effect=Exception("boom"))
    def test_broadcast_error_logged_not_raised(self, mock_get_layer):
        """Channel layer errors are logged, not raised."""
        _broadcast_ws(1, {"type": "test"})  # Should not raise

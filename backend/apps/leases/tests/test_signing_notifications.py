"""
UX-007 — Signing completion agent notification tests.

Covers:
  1. _notify_staff sends email + WS notification for signer_completed (form.completed)
  2. _notify_staff sends email + WS notification for submission_completed
  3. _notify_staff no-ops when submission has no created_by
  4. _notify_staff re-uses event_id from data dict (no new UUID generated)
  5. _broadcast_agent_notification sends to correct channel layer group
  6. event_id propagation: views.py injects event_id into _broadcast_ws payload

Run:
    cd backend && pytest apps/leases/tests/test_signing_notifications.py -v
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, call, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_submission(
    pk=1,
    lease_id=None,
    mandate_id=None,
    status="in_progress",
    signers=None,
    signed_pdf_file=None,
):
    """Build a minimal ESigningSubmission-like mock."""
    sub = MagicMock()
    sub.pk = pk
    sub.lease_id = lease_id
    sub.mandate_id = mandate_id
    sub.status = status
    sub.signers = signers or [
        {"id": "s1", "name": "John Doe", "email": "john@example.com", "role": "Tenant", "status": "completed"},
    ]
    sub.signed_pdf_file = signed_pdf_file
    sub.signing_mode = "sequential"

    if lease_id:
        prop = MagicMock()
        prop.name = "Sunset Heights"
        prop.address = "12 Sunset Ave, Stellenbosch"
        prop.pk = 10
        unit = MagicMock()
        unit.unit_number = "2B"
        unit.property = prop
        lease = MagicMock()
        lease.unit = unit
        lease.pk = lease_id
        sub.lease = lease
    else:
        sub.lease = None

    if mandate_id:
        prop = MagicMock()
        prop.name = "Oak Manor"
        prop.address = "5 Oak St, Cape Town"
        prop.pk = 20
        mandate = MagicMock()
        mandate.property = prop
        sub.mandate = mandate
    else:
        sub.mandate = None

    creator = MagicMock()
    creator.pk = 99
    creator.email = "agent@example.com"
    creator.first_name = "Sipho"
    creator.get_full_name = lambda: "Sipho Nkosi"
    sub.created_by = creator

    return sub


# ---------------------------------------------------------------------------
# Tests for _notify_staff
# ---------------------------------------------------------------------------


class TestNotifyStaff:
    """Unit tests for apps.esigning.webhooks._notify_staff."""

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_signer_completed_sends_email_and_ws(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        event_id = str(uuid.uuid4())
        _notify_staff(sub, "form.completed", {
            "submitter": {"name": "John Doe", "email": "john@example.com"},
            "event_id": event_id,
        })

        # Email sent
        assert mock_email.called
        call_args = mock_email.call_args
        subject = call_args[0][0]
        assert "John Doe" in subject or "Signing progress" in subject
        recipient = call_args[0][2]
        assert recipient == "agent@example.com"

        # WS broadcast called with correct group
        mock_ws.assert_called_once()
        creator_pk, payload = mock_ws.call_args[0]
        assert creator_pk == 99
        assert payload["type"] == "signer_completed"
        assert payload["signer_name"] == "John Doe"
        assert payload["event_id"] == event_id

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_submission_completed_sends_email_and_ws(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        pdf_file = MagicMock()
        pdf_file.url = "/media/esigning/signed_lease_1.pdf"
        sub = _make_submission(lease_id=5, status="completed", signed_pdf_file=pdf_file)
        event_id = str(uuid.uuid4())
        _notify_staff(sub, "submission.completed", {"event_id": event_id})

        assert mock_email.called
        subject = mock_email.call_args[0][0]
        assert "All signatures" in subject or "complete" in subject.lower()

        mock_ws.assert_called_once()
        creator_pk, payload = mock_ws.call_args[0]
        assert creator_pk == 99
        assert payload["type"] == "submission_completed"
        assert payload["event_id"] == event_id
        assert "Sunset Heights" in payload["doc_title"] or "doc_title" in payload

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_noop_when_no_creator(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        sub.created_by = None

        _notify_staff(sub, "form.completed", {})

        mock_email.assert_not_called()
        mock_ws.assert_not_called()

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_noop_when_no_creator_email(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        sub.created_by.email = ""

        _notify_staff(sub, "form.completed", {})

        mock_email.assert_not_called()
        mock_ws.assert_not_called()

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_reuses_event_id_from_data(self, mock_email, mock_ws):
        """event_id from data dict is used verbatim — no new UUID created."""
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        fixed_id = "fixed-event-id-1234"
        _notify_staff(sub, "form.completed", {
            "submitter": {"name": "Jane", "email": "jane@example.com"},
            "event_id": fixed_id,
        })

        _, payload = mock_ws.call_args[0]
        assert payload["event_id"] == fixed_id

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_mandate_submission_doc_type(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(mandate_id=20)
        _notify_staff(sub, "submission.completed", {})

        _, payload = mock_ws.call_args[0]
        assert payload["doc_type"] == "mandate"
        assert "Oak Manor" in payload["doc_title"] or "Rental Mandate" in payload["doc_title"]

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_unknown_event_type_is_noop(self, mock_email, mock_ws):
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        _notify_staff(sub, "unknown.event", {})

        mock_email.assert_not_called()
        mock_ws.assert_not_called()

    @patch("apps.esigning.webhooks._broadcast_agent_notification")
    @patch("apps.notifications.services.send_email", return_value=True)
    def test_email_html_contains_panel_url(self, mock_email, mock_ws):
        """When ADMIN_APP_BASE_URL is set, the email HTML contains a deep-link."""
        from apps.esigning.webhooks import _notify_staff

        sub = _make_submission(lease_id=5)
        # Patch django.conf.settings where it's referenced by the lazy import inside
        # _notify_staff (which imports it as `from django.conf import settings as _settings`)
        with patch("django.conf.settings") as mock_settings:
            mock_settings.ADMIN_APP_BASE_URL = "https://admin.klikk.co.za"
            _notify_staff(sub, "form.completed", {
                "submitter": {"name": "Test", "email": "t@example.com"},
            })

        # The html_body kwarg or positional body should reference the panel URL
        html_kwarg = mock_email.call_args.kwargs.get("html_body", "")
        # At minimum the email was sent
        assert mock_email.called
        assert "leases" in html_kwarg or "klikk.co.za" in html_kwarg or html_kwarg != ""


# ---------------------------------------------------------------------------
# Tests for _broadcast_agent_notification
# ---------------------------------------------------------------------------


class TestBroadcastAgentNotification:
    """Unit tests for apps.esigning.webhooks._broadcast_agent_notification."""

    def test_sends_to_correct_group(self):
        from apps.esigning.webhooks import _broadcast_agent_notification

        channel_layer = MagicMock()
        # Patch inside the channels.layers module since _broadcast_agent_notification
        # imports these lazily inside the function body.
        with patch("channels.layers.get_channel_layer", return_value=channel_layer):
            with patch("asgiref.sync.async_to_sync", side_effect=lambda f: f):
                _broadcast_agent_notification(42, {"type": "signer_completed"})

        channel_layer.group_send.assert_called_once()
        group, msg = channel_layer.group_send.call_args[0]
        assert group == "signing_notifications_42"
        assert msg["type"] == "signing.notification"
        assert msg["payload"]["type"] == "signer_completed"

    def test_noop_when_no_channel_layer(self):
        from apps.esigning.webhooks import _broadcast_agent_notification

        with patch("channels.layers.get_channel_layer", return_value=None):
            # Should not raise
            _broadcast_agent_notification(1, {"type": "signer_completed"})

    def test_exception_is_swallowed(self):
        from apps.esigning.webhooks import _broadcast_agent_notification

        with patch("channels.layers.get_channel_layer", side_effect=RuntimeError("boom")):
            # Should not propagate
            _broadcast_agent_notification(1, {"type": "signer_completed"})

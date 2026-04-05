"""
Unit tests for apps/esigning/audit.py.

Tests log_esigning_event() helper: creates ESigningAuditEvent with correct fields.
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


class TestLogESigningEvent:
    """log_esigning_event() creates audit events with correct fields."""

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_creates_event_with_required_fields(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_event = MagicMock()
        mock_qs.create.return_value = mock_event

        submission = MagicMock()
        user = MagicMock()

        log_esigning_event(
            submission=submission,
            event_type=ESigningAuditEvent.EventType.SIGNATURE_APPLIED,
            signer_role="tenant_1",
            user=user,
        )

        mock_qs.create.assert_called_once()
        kwargs = mock_qs.create.call_args[1]
        assert kwargs["submission"] is submission
        assert kwargs["event_type"] == "signature_applied"
        assert kwargs["signer_role"] == "tenant_1"
        assert kwargs["user"] is user

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_ip_is_none_when_no_request(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_qs.create.return_value = MagicMock()
        submission = MagicMock()

        log_esigning_event(
            submission=submission,
            event_type=ESigningAuditEvent.EventType.DOCUMENT_VIEWED,
        )

        kwargs = mock_qs.create.call_args[1]
        assert kwargs["ip_address"] is None
        assert kwargs["user_agent"] == ""

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_extracts_ip_from_request(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_qs.create.return_value = MagicMock()
        submission = MagicMock()

        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "192.168.1.50",
            "HTTP_USER_AGENT": "Mozilla/5.0 Test",
            "HTTP_X_FORWARDED_FOR": "",
        }

        log_esigning_event(
            submission=submission,
            event_type=ESigningAuditEvent.EventType.CONSENT_GIVEN,
            request=request,
        )

        kwargs = mock_qs.create.call_args[1]
        assert kwargs["ip_address"] == "192.168.1.50"
        assert kwargs["user_agent"] == "Mozilla/5.0 Test"

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_extracts_ip_from_x_forwarded_for(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_qs.create.return_value = MagicMock()
        submission = MagicMock()

        request = MagicMock()
        request.META.get = lambda k, default="": {
            "HTTP_X_FORWARDED_FOR": "10.0.0.1, 172.16.0.1",
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "",
        }.get(k, default)

        log_esigning_event(
            submission=submission,
            event_type=ESigningAuditEvent.EventType.LINK_CREATED,
            request=request,
        )

        kwargs = mock_qs.create.call_args[1]
        # Should use the first IP from X-Forwarded-For
        assert kwargs["ip_address"] == "10.0.0.1"

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_metadata_defaults_to_empty_dict(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_qs.create.return_value = MagicMock()

        log_esigning_event(
            submission=MagicMock(),
            event_type=ESigningAuditEvent.EventType.SIGNING_COMPLETED,
        )

        kwargs = mock_qs.create.call_args[1]
        assert kwargs["metadata"] == {}

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_metadata_passed_through(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        mock_qs.create.return_value = MagicMock()

        log_esigning_event(
            submission=MagicMock(),
            event_type=ESigningAuditEvent.EventType.DOCUMENT_COMPLETED,
            metadata={"source": "public_link", "page": 3},
        )

        kwargs = mock_qs.create.call_args[1]
        assert kwargs["metadata"] == {"source": "public_link", "page": 3}

    @patch("apps.esigning.audit.ESigningAuditEvent.objects")
    def test_returns_created_event(self, mock_qs):
        from apps.esigning.audit import log_esigning_event
        from apps.esigning.models import ESigningAuditEvent

        expected_event = MagicMock()
        mock_qs.create.return_value = expected_event

        result = log_esigning_event(
            submission=MagicMock(),
            event_type=ESigningAuditEvent.EventType.LINK_EXPIRED,
        )

        assert result is expected_event

"""
Unit tests for notification service functions in apps/notifications/services.py.

All external calls (Twilio, Django email) are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = [pytest.mark.unit, pytest.mark.green]


# ---------------------------------------------------------------------------
# normalize_phone_e164
# ---------------------------------------------------------------------------
class TestNormalizePhoneE164:
    """Phone number normalisation helper."""

    def test_empty_string_returns_empty(self):
        from apps.notifications.services import normalize_phone_e164

        assert normalize_phone_e164("") == ""

    def test_none_returns_empty(self):
        from apps.notifications.services import normalize_phone_e164

        assert normalize_phone_e164(None) == ""

    def test_leading_zero_replaced_with_default_dial_code(self):
        from apps.notifications.services import normalize_phone_e164

        with patch("apps.notifications.services.settings") as mock_s:
            mock_s.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
            result = normalize_phone_e164("0821234567")
        assert result == "+27821234567"

    def test_already_e164_unchanged(self):
        from apps.notifications.services import normalize_phone_e164

        result = normalize_phone_e164("+27821234567")
        assert result == "+27821234567"

    def test_strips_whitespace_and_dashes(self):
        from apps.notifications.services import normalize_phone_e164

        with patch("apps.notifications.services.settings") as mock_s:
            mock_s.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
            result = normalize_phone_e164("082-123 4567")
        assert result == "+27821234567"

    def test_strips_parentheses(self):
        from apps.notifications.services import normalize_phone_e164

        with patch("apps.notifications.services.settings") as mock_s:
            mock_s.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
            result = normalize_phone_e164("(082) 123 4567")
        assert result == "+27821234567"

    def test_national_prefix_gets_plus(self):
        """Number starting with the national code (e.g. 27...) gets a + prepended."""
        from apps.notifications.services import normalize_phone_e164

        with patch("apps.notifications.services.settings") as mock_s:
            mock_s.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
            result = normalize_phone_e164("27821234567")
        assert result == "+27821234567"


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------
class TestSendEmail:
    """send_email(): sends via Django EmailMultiAlternatives."""

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_success_returns_true(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        result = send_email("Subject", "Body", "user@example.com")

        assert result is True
        mock_msg.send.assert_called_once_with(fail_silently=False)

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_success_creates_sent_log(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_email_cls.return_value = MagicMock()

        send_email("Subject", "Body", "user@example.com")

        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["channel"] == "email"
        assert kwargs["to_address"] == "user@example.com"
        assert kwargs["status"] == "sent"
        assert kwargs["subject"] == "Subject"

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_failure_returns_false(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_msg = MagicMock()
        mock_msg.send.side_effect = Exception("SMTP error")
        mock_email_cls.return_value = mock_msg

        result = send_email("Subject", "Body", "user@example.com")

        assert result is False

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_failure_creates_failed_log_with_error(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_msg = MagicMock()
        mock_msg.send.side_effect = Exception("SMTP error")
        mock_email_cls.return_value = mock_msg

        send_email("Subject", "Body", "user@example.com")

        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["status"] == "failed"
        assert "SMTP error" in kwargs["error_message"]

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_multiple_recipients_logs_each(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_email_cls.return_value = MagicMock()

        send_email("Subject", "Body", ["a@b.com", "c@d.com"])

        assert mock_log_create.call_count == 2
        logged_addrs = [c[1]["to_address"] for c in mock_log_create.call_args_list]
        assert "a@b.com" in logged_addrs
        assert "c@d.com" in logged_addrs

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_multiple_recipients_first_is_to_rest_are_cc(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_email_cls.return_value = MagicMock()

        send_email("Subject", "Body", ["a@b.com", "c@d.com", "e@f.com"])

        mock_email_cls.assert_called_once()
        kwargs = mock_email_cls.call_args[1]
        assert kwargs["to"] == ["a@b.com"]
        assert kwargs["cc"] == ["c@d.com", "e@f.com"]

    def test_empty_recipients_returns_false(self):
        from apps.notifications.services import send_email

        result = send_email("Subject", "Body", [])
        assert result is False

    def test_string_recipient_converted_to_list(self):
        """A single string recipient should be treated as a one-element list."""
        from apps.notifications.services import send_email

        with patch("apps.notifications.services.EmailMultiAlternatives") as mock_cls:
            with patch("apps.notifications.services.NotificationLog.objects.create"):
                mock_cls.return_value = MagicMock()
                send_email("Sub", "Body", "solo@test.com")

        kwargs = mock_cls.call_args[1]
        assert kwargs["to"] == ["solo@test.com"]
        assert kwargs["cc"] is None

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_html_body_attached_as_alternative(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        send_email("Sub", "plain", "a@b.com", html_body="<b>html</b>")

        mock_msg.attach_alternative.assert_called_once_with("<b>html</b>", "text/html")

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_no_html_body_skips_alternative(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_msg = MagicMock()
        mock_email_cls.return_value = mock_msg

        send_email("Sub", "plain", "a@b.com")

        mock_msg.attach_alternative.assert_not_called()

    @patch("apps.notifications.services.EmailMultiAlternatives")
    @patch("apps.notifications.services.NotificationLog.objects.create")
    def test_custom_from_email(self, mock_log_create, mock_email_cls):
        from apps.notifications.services import send_email

        mock_email_cls.return_value = MagicMock()

        send_email("Sub", "Body", "a@b.com", from_email="custom@sender.com")

        kwargs = mock_email_cls.call_args[1]
        assert kwargs["from_email"] == "custom@sender.com"


# ---------------------------------------------------------------------------
# send_sms
# ---------------------------------------------------------------------------
class TestSendSms:
    """send_sms(): sends via Twilio client."""

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_success_returns_true(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_sms

        mock_settings.TWILIO_SMS_FROM = "+15551234567"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "SM123"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        result = send_sms("+27821234567", "Hello")

        assert result is True
        client.messages.create.assert_called_once_with(
            to="+27821234567", from_="+15551234567", body="Hello"
        )

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_success_creates_sent_log_with_sid(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_sms

        mock_settings.TWILIO_SMS_FROM = "+15551234567"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "SM123abc"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        send_sms("+27821234567", "Hello")

        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["channel"] == "sms"
        assert kwargs["status"] == "sent"
        assert kwargs["provider_message_id"] == "SM123abc"

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_failure_returns_false_and_logs_error(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_sms

        mock_settings.TWILIO_SMS_FROM = "+15551234567"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        client.messages.create.side_effect = Exception("Twilio down")
        mock_client_fn.return_value = client

        result = send_sms("+27821234567", "Hello")

        assert result is False
        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["status"] == "failed"
        assert "Twilio down" in kwargs["error_message"]

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_no_twilio_config_returns_false(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_sms

        mock_settings.TWILIO_SMS_FROM = ""
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        mock_client_fn.return_value = None

        result = send_sms("+27821234567", "Hello")

        assert result is False

    def test_empty_phone_returns_false(self):
        from apps.notifications.services import send_sms

        result = send_sms("", "Hello")
        assert result is False

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_phone_normalisation_leading_zero(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_sms

        mock_settings.TWILIO_SMS_FROM = "+15551234567"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "SM999"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        send_sms("0821234567", "Hi")

        client.messages.create.assert_called_once_with(
            to="+27821234567", from_="+15551234567", body="Hi"
        )


# ---------------------------------------------------------------------------
# send_whatsapp
# ---------------------------------------------------------------------------
class TestSendWhatsapp:
    """send_whatsapp(): sends via Twilio with whatsapp: prefix."""

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_success_returns_true(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_whatsapp

        mock_settings.TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "WA123"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        result = send_whatsapp("+27821234567", "Hello WA")

        assert result is True
        client.messages.create.assert_called_once_with(
            to="whatsapp:+27821234567", from_="whatsapp:+14155238886", body="Hello WA"
        )

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_success_creates_sent_log(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_whatsapp

        mock_settings.TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "WA456"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        send_whatsapp("+27821234567", "Hello WA")

        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["channel"] == "whatsapp"
        assert kwargs["status"] == "sent"
        assert kwargs["provider_message_id"] == "WA456"

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_failure_returns_false_and_logs_error(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_whatsapp

        mock_settings.TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        client.messages.create.side_effect = Exception("WA failed")
        mock_client_fn.return_value = client

        result = send_whatsapp("+27821234567", "Hello WA")

        assert result is False
        mock_log_create.assert_called_once()
        kwargs = mock_log_create.call_args[1]
        assert kwargs["status"] == "failed"
        assert "WA failed" in kwargs["error_message"]

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_no_twilio_config_returns_false(self, mock_settings, mock_client_fn, mock_log_create):
        from apps.notifications.services import send_whatsapp

        mock_settings.TWILIO_WHATSAPP_FROM = ""
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        mock_client_fn.return_value = None

        result = send_whatsapp("+27821234567", "Hello")

        assert result is False

    def test_empty_phone_returns_false(self):
        from apps.notifications.services import send_whatsapp

        result = send_whatsapp("", "Hello")
        assert result is False

    @patch("apps.notifications.services.NotificationLog.objects.create")
    @patch("apps.notifications.services._twilio_client")
    @patch("apps.notifications.services.settings")
    def test_from_without_whatsapp_prefix_gets_prefixed(self, mock_settings, mock_client_fn, mock_log_create):
        """If TWILIO_WHATSAPP_FROM lacks the whatsapp: prefix, it's added."""
        from apps.notifications.services import send_whatsapp

        mock_settings.TWILIO_WHATSAPP_FROM = "+14155238886"
        mock_settings.NOTIFICATIONS_DEFAULT_DIAL_CODE = "+27"
        client = MagicMock()
        msg = MagicMock()
        msg.sid = "WA789"
        client.messages.create.return_value = msg
        mock_client_fn.return_value = client

        send_whatsapp("+27821234567", "Test")

        client.messages.create.assert_called_once_with(
            to="whatsapp:+27821234567", from_="whatsapp:+14155238886", body="Test"
        )


# ---------------------------------------------------------------------------
# notify_sms_and_whatsapp
# ---------------------------------------------------------------------------
class TestNotifySmsAndWhatsapp:
    """notify_sms_and_whatsapp(): sends via both channels."""

    @patch("apps.notifications.services.send_whatsapp", return_value=True)
    @patch("apps.notifications.services.send_sms", return_value=True)
    def test_both_succeed(self, mock_sms, mock_wa):
        from apps.notifications.services import notify_sms_and_whatsapp

        result = notify_sms_and_whatsapp("+27821234567", "Dual message")

        assert result == {"sms": True, "whatsapp": True}
        mock_sms.assert_called_once_with("+27821234567", "Dual message")
        mock_wa.assert_called_once_with("+27821234567", "Dual message")

    @patch("apps.notifications.services.send_whatsapp", return_value=True)
    @patch("apps.notifications.services.send_sms", return_value=False)
    def test_sms_fails_whatsapp_succeeds(self, mock_sms, mock_wa):
        from apps.notifications.services import notify_sms_and_whatsapp

        result = notify_sms_and_whatsapp("+27821234567", "Partial")

        assert result == {"sms": False, "whatsapp": True}

    @patch("apps.notifications.services.send_whatsapp", return_value=False)
    @patch("apps.notifications.services.send_sms", return_value=True)
    def test_sms_succeeds_whatsapp_fails(self, mock_sms, mock_wa):
        from apps.notifications.services import notify_sms_and_whatsapp

        result = notify_sms_and_whatsapp("+27821234567", "Partial")

        assert result == {"sms": True, "whatsapp": False}

    @patch("apps.notifications.services.send_whatsapp", return_value=False)
    @patch("apps.notifications.services.send_sms", return_value=False)
    def test_both_fail(self, mock_sms, mock_wa):
        from apps.notifications.services import notify_sms_and_whatsapp

        result = notify_sms_and_whatsapp("+27821234567", "Both fail")

        assert result == {"sms": False, "whatsapp": False}


# ---------------------------------------------------------------------------
# _truncate_body helper
# ---------------------------------------------------------------------------
class TestTruncateBody:
    """_truncate_body(): truncates long body text."""

    def test_short_body_unchanged(self):
        from apps.notifications.services import _truncate_body

        assert _truncate_body("short") == "short"

    def test_long_body_truncated(self):
        from apps.notifications.services import _truncate_body, _BODY_LOG_MAX

        long_text = "x" * (_BODY_LOG_MAX + 100)
        result = _truncate_body(long_text)
        assert len(result) == _BODY_LOG_MAX + 1  # +1 for the ellipsis character
        assert result.endswith("\u2026")

    def test_exact_limit_not_truncated(self):
        from apps.notifications.services import _truncate_body, _BODY_LOG_MAX

        exact = "x" * _BODY_LOG_MAX
        assert _truncate_body(exact) == exact


# ---------------------------------------------------------------------------
# _twilio_client
# ---------------------------------------------------------------------------
class TestTwilioClient:
    """_twilio_client(): returns None when credentials missing."""

    @patch("apps.notifications.services.settings")
    def test_returns_none_when_no_sid(self, mock_settings):
        from apps.notifications.services import _twilio_client

        mock_settings.TWILIO_ACCOUNT_SID = ""
        mock_settings.TWILIO_AUTH_TOKEN = "token"

        assert _twilio_client() is None

    @patch("apps.notifications.services.settings")
    def test_returns_none_when_no_token(self, mock_settings):
        from apps.notifications.services import _twilio_client

        mock_settings.TWILIO_ACCOUNT_SID = "sid"
        mock_settings.TWILIO_AUTH_TOKEN = ""

        assert _twilio_client() is None

    @patch("apps.notifications.services.settings")
    def test_returns_client_when_configured(self, mock_settings):
        """Returns a Twilio Client instance when both SID and token are set."""
        from apps.notifications.services import _twilio_client

        mock_settings.TWILIO_ACCOUNT_SID = "ACtest123"
        mock_settings.TWILIO_AUTH_TOKEN = "authtoken456"

        mock_client_cls = MagicMock()
        mock_twilio_rest = MagicMock()
        mock_twilio_rest.Client = mock_client_cls

        with patch.dict("sys.modules", {"twilio.rest": mock_twilio_rest}):
            result = _twilio_client()

        mock_client_cls.assert_called_once_with("ACtest123", "authtoken456")
        assert result is not None


# ---------------------------------------------------------------------------
# deliver_otp_sms
# ---------------------------------------------------------------------------
class TestDeliverOtpSms:
    """deliver_otp_sms(): convenience wrapper around send_sms."""

    @patch("apps.notifications.services.send_sms", return_value=True)
    def test_calls_send_sms_with_formatted_body(self, mock_send_sms):
        from apps.notifications.services import deliver_otp_sms

        result = deliver_otp_sms("0821234567", "123456")

        assert result is True
        mock_send_sms.assert_called_once_with(
            "0821234567",
            "Your verification code is: 123456. It expires in 10 minutes.",
        )

    @patch("apps.notifications.services.send_sms", return_value=False)
    def test_returns_false_on_failure(self, mock_send_sms):
        from apps.notifications.services import deliver_otp_sms

        result = deliver_otp_sms("0821234567", "654321")
        assert result is False

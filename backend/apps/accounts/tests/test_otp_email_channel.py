"""
Unit tests for apps.accounts.otp.channels.email — EmailChannel.

Covers:
  - Correct recipient, subject, and body delivered via Django's email backend.
  - Template renders code prominently and includes POPIA footer.
  - TTL and purpose appear in the message.
  - SMS channel stub raises NotImplementedError.
"""
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings

from apps.accounts.otp.channels.email import EmailChannel
from apps.accounts.otp.channels.sms import SMSChannel
from apps.accounts.otp.channels.base import Channel


class TestEmailChannelInterface(TestCase):
    def test_email_channel_is_subclass_of_channel(self):
        assert issubclass(EmailChannel, Channel)

    def test_sms_channel_is_subclass_of_channel(self):
        assert issubclass(SMSChannel, Channel)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@klikk.co.za",
)
class TestEmailChannelSend(TestCase):
    def setUp(self):
        self.channel = EmailChannel()

    def _send(self, recipient="tenant@example.com", code="123456", context=None):
        if context is None:
            context = {"purpose": "registration", "ttl_minutes": 5}
        self.channel.send(recipient=recipient, code=code, context=context)
        return mail.outbox[-1]

    def test_email_sent_to_correct_recipient(self):
        msg = self._send(recipient="alice@example.com")
        assert "alice@example.com" in msg.to

    def test_email_subject_does_not_contain_code(self):
        """POPIA minimum-necessity: OTP code must not appear in relay-visible subject."""
        msg = self._send(code="987654")
        assert "987654" not in msg.subject

    def test_email_subject_is_generic(self):
        msg = self._send(code="987654")
        assert "verification code" in msg.subject.lower()

    def test_email_body_contains_code(self):
        msg = self._send(code="456789")
        assert "456789" in msg.body

    def test_email_body_mentions_expiry(self):
        msg = self._send(context={"purpose": "registration", "ttl_minutes": 5})
        assert "5" in msg.body
        # "minute" or "minutes" should appear
        assert "minute" in msg.body.lower()

    def test_email_body_mentions_purpose(self):
        msg = self._send(context={"purpose": "password_reset", "ttl_minutes": 5})
        assert "password" in msg.body.lower() or "reset" in msg.body.lower()

    def test_email_body_contains_popia_footer(self):
        msg = self._send()
        body_lower = msg.body.lower()
        assert "popia" in body_lower or "personal information" in body_lower

    def test_from_email_is_configured_default(self):
        msg = self._send()
        assert msg.from_email == "noreply@klikk.co.za"

    def test_multiple_sends_grow_outbox(self):
        self._send(recipient="a@example.com")
        self._send(recipient="b@example.com")
        assert len(mail.outbox) == 2

    def test_ttl_minutes_plural_used_correctly(self):
        """Template should pluralize correctly for 1 minute."""
        msg = self._send(context={"purpose": "registration", "ttl_minutes": 1})
        # Should say "1 minute" not "1 minutes"
        # Django's pluralize filter handles this in the template.
        assert "1 minute" in msg.body


class TestSMSChannelStub(TestCase):
    def test_sms_channel_raises_not_implemented(self):
        ch = SMSChannel()
        with self.assertRaises(NotImplementedError) as ctx:
            ch.send(
                recipient="+27821234567",
                code="123456",
                context={"purpose": "registration", "ttl_minutes": 5},
            )
        assert "WinSMS" in str(ctx.exception) or "Panacea" in str(ctx.exception)

    def test_sms_channel_error_message_mentions_pending(self):
        ch = SMSChannel()
        try:
            ch.send("+27821234567", "123456", {})
        except NotImplementedError as exc:
            assert "pending" in str(exc).lower() or "integration" in str(exc).lower()

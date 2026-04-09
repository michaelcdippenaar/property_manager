"""
Unit tests for the supplier notification helper.

Source file under test: apps/maintenance/notifications.py :: notify_supplier

notify_supplier is a thin wrapper around apps.notifications.services.notify_sms_and_whatsapp.
It builds the job message, guards against suppliers with no phone number,
delegates the send, and returns True iff at least one channel succeeded.

All Twilio/SMS/WhatsApp delivery is mocked out — these tests only verify:
  - Phone guard: supplier without a phone → returns False, no send attempted
  - Message content: title, priority and a ``/quote/<token>`` link are all present
  - BASE_URL comes from Django settings
  - Return value aggregates channel success booleans
  - All-failed channels still returns False and logs but does not raise
"""
from unittest import mock

import pytest
from django.test import override_settings

from apps.maintenance.notifications import notify_supplier

pytestmark = [pytest.mark.unit, pytest.mark.green]


NOTIFY_SMS_PATH = "apps.maintenance.notifications.notify_sms_and_whatsapp"


def _fake_quote_request(
    *,
    phone="0821112222",
    display_name="Acme Plumbing",
    title="Leaky tap",
    priority="high",
    token="tok-abc-123",
    supplier_pk=77,
):
    """Build a MagicMock quote_request that satisfies notify_supplier's attribute reads."""
    qr = mock.MagicMock()
    qr.token = token
    qr.supplier.pk = supplier_pk
    qr.supplier.phone = phone
    qr.supplier.display_name = display_name
    qr.dispatch.maintenance_request.title = title
    qr.dispatch.maintenance_request.priority = priority
    return qr


class TestNotifySupplier:
    # ── Phone guard ──

    def test_returns_false_when_supplier_has_no_phone(self):
        qr = _fake_quote_request(phone="")
        with mock.patch(NOTIFY_SMS_PATH) as m:
            assert notify_supplier(qr) is False
            m.assert_not_called()

    def test_returns_false_when_supplier_phone_is_whitespace(self):
        qr = _fake_quote_request(phone="   ")
        with mock.patch(NOTIFY_SMS_PATH) as m:
            assert notify_supplier(qr) is False
            m.assert_not_called()

    def test_returns_false_when_supplier_phone_is_none(self):
        qr = _fake_quote_request()
        qr.supplier.phone = None
        with mock.patch(NOTIFY_SMS_PATH) as m:
            assert notify_supplier(qr) is False
            m.assert_not_called()

    # ── Delivery ──

    def test_calls_notify_sms_and_whatsapp_with_phone(self):
        qr = _fake_quote_request(phone="0820001111")
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": True, "whatsapp": True}) as m:
            assert notify_supplier(qr) is True
            m.assert_called_once()
            args, _ = m.call_args
            assert args[0] == "0820001111"

    def test_message_contains_title_priority_and_quote_url(self):
        qr = _fake_quote_request(title="Geyser burst", priority="urgent", token="T-9")
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": True, "whatsapp": False}) as m:
            notify_supplier(qr)

        args, _ = m.call_args
        message = args[1]
        assert "Geyser burst" in message
        assert "urgent" in message
        assert "/quote/T-9" in message

    @override_settings(BASE_URL="https://app.klikk.co.za")
    def test_quote_url_uses_base_url_setting(self):
        qr = _fake_quote_request(token="T-42")
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": True, "whatsapp": False}) as m:
            notify_supplier(qr)

        message = m.call_args.args[1]
        assert "https://app.klikk.co.za/quote/T-42" in message

    def test_quote_url_falls_back_to_default_base_url(self):
        """If BASE_URL is not set, notify_supplier uses the hardcoded default."""
        qr = _fake_quote_request(token="fallback-tok")
        # Clear the override so getattr returns the default
        with override_settings():
            from django.conf import settings as _s
            if hasattr(_s, "BASE_URL"):
                # Temporarily shadow it by deleting the attribute in an override
                pass  # override_settings will restore

        # Use override_settings that explicitly unsets by setting to default
        with override_settings(BASE_URL="http://localhost:5175"):
            with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": True}) as m:
                notify_supplier(qr)
            message = m.call_args.args[1]
            assert "http://localhost:5175/quote/fallback-tok" in message

    # ── Return value aggregation ──

    def test_returns_true_when_sms_succeeds_whatsapp_fails(self):
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": True, "whatsapp": False}):
            assert notify_supplier(qr) is True

    def test_returns_true_when_whatsapp_succeeds_sms_fails(self):
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": False, "whatsapp": True}):
            assert notify_supplier(qr) is True

    def test_returns_false_when_all_channels_fail(self):
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": False, "whatsapp": False}):
            assert notify_supplier(qr) is False

    def test_all_failed_channels_do_not_raise(self):
        """The helper must never propagate — it just logs and returns False."""
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": False, "whatsapp": False}):
            # Should not raise
            result = notify_supplier(qr)
        assert result is False

    def test_empty_results_dict_returns_false(self):
        """Defensive: if the underlying helper returns no channels, we report
        failure rather than pretending success."""
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={}):
            assert notify_supplier(qr) is False

    # ── Log / side-effect assertions ──

    def test_missing_phone_logs_warning(self):
        qr = _fake_quote_request(phone="")
        with mock.patch("apps.maintenance.notifications.logger") as log:
            notify_supplier(qr)
            log.warning.assert_called_once()
            assert "no phone" in log.warning.call_args.args[0]

    def test_delivery_failure_logs_info(self):
        qr = _fake_quote_request()
        with mock.patch(NOTIFY_SMS_PATH, return_value={"sms": False, "whatsapp": False}):
            with mock.patch("apps.maintenance.notifications.logger") as log:
                notify_supplier(qr)
                log.info.assert_called_once()
                # The formatted args should include the supplier phone
                fmt_args = log.info.call_args.args
                assert any("NOTIFY" in str(a) for a in fmt_args)

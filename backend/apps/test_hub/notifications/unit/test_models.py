"""
Unit tests for the NotificationLog model and related enums.

Tests run without database access where possible (using model instantiation only).
"""
import pytest
from unittest.mock import MagicMock
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestNotificationChannel:
    """NotificationChannel TextChoices."""

    def test_email_choice_exists(self):
        from apps.notifications.models import NotificationChannel

        choices = [c[0] for c in NotificationChannel.choices]
        assert "email" in choices

    def test_sms_choice_exists(self):
        from apps.notifications.models import NotificationChannel

        choices = [c[0] for c in NotificationChannel.choices]
        assert "sms" in choices

    def test_whatsapp_choice_exists(self):
        from apps.notifications.models import NotificationChannel

        choices = [c[0] for c in NotificationChannel.choices]
        assert "whatsapp" in choices

    def test_exactly_three_channels(self):
        from apps.notifications.models import NotificationChannel

        assert len(NotificationChannel.choices) == 3


class TestNotificationStatus:
    """NotificationStatus TextChoices."""

    def test_pending_choice_exists(self):
        from apps.notifications.models import NotificationStatus

        choices = [c[0] for c in NotificationStatus.choices]
        assert "pending" in choices

    def test_sent_choice_exists(self):
        from apps.notifications.models import NotificationStatus

        choices = [c[0] for c in NotificationStatus.choices]
        assert "sent" in choices

    def test_failed_choice_exists(self):
        from apps.notifications.models import NotificationStatus

        choices = [c[0] for c in NotificationStatus.choices]
        assert "failed" in choices

    def test_exactly_three_statuses(self):
        from apps.notifications.models import NotificationStatus

        assert len(NotificationStatus.choices) == 3


class TestNotificationLogModel:
    """NotificationLog model fields and __str__."""

    def _make_instance(self, **overrides):
        """Create a NotificationLog instance without hitting the DB."""
        from apps.notifications.models import NotificationLog

        obj = NotificationLog.__new__(NotificationLog)
        obj._state = ModelState()
        obj.channel = overrides.get("channel", "email")
        obj.to_address = overrides.get("to_address", "user@example.com")
        obj.subject = overrides.get("subject", "Test Subject")
        obj.body = overrides.get("body", "Test body")
        obj.status = overrides.get("status", "pending")
        obj.provider_message_id = overrides.get("provider_message_id", "")
        obj.error_message = overrides.get("error_message", "")
        return obj

    def test_str_email_pending(self):
        obj = self._make_instance(channel="email", to_address="a@b.com", status="pending")
        assert str(obj) == "email \u2192 a@b.com (pending)"

    def test_str_sms_sent(self):
        obj = self._make_instance(channel="sms", to_address="+27821234567", status="sent")
        assert str(obj) == "sms \u2192 +27821234567 (sent)"

    def test_str_whatsapp_failed(self):
        obj = self._make_instance(channel="whatsapp", to_address="whatsapp:+27821234567", status="failed")
        assert str(obj) == "whatsapp \u2192 whatsapp:+27821234567 (failed)"

    def test_default_status_is_pending(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("status")
        assert field.default == "pending"

    def test_channel_max_length(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("channel")
        assert field.max_length == 16

    def test_to_address_max_length(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("to_address")
        assert field.max_length == 320

    def test_subject_max_length_and_blank(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("subject")
        assert field.max_length == 255
        assert field.blank is True

    def test_provider_message_id_max_length_and_blank(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("provider_message_id")
        assert field.max_length == 128
        assert field.blank is True

    def test_error_message_is_blank_textfield(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("error_message")
        assert field.blank is True

    def test_created_at_auto_now_add(self):
        from apps.notifications.models import NotificationLog

        field = NotificationLog._meta.get_field("created_at")
        assert field.auto_now_add is True

    def test_ordering_is_descending_created_at(self):
        from apps.notifications.models import NotificationLog

        assert NotificationLog._meta.ordering == ["-created_at"]

    def test_indexes_include_created_at_and_channel_status(self):
        from apps.notifications.models import NotificationLog

        index_fields = [tuple(idx.fields) for idx in NotificationLog._meta.indexes]
        assert ("-created_at",) in index_fields
        assert ("channel", "status") in index_fields

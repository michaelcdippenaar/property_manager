"""
Unit tests for apps.contact models.

Covers ContactEnquiry model fields, __str__, mark_responded, and anonymise.
These run without a DB (model instantiation only).
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


def _make_enquiry(**kwargs):
    """Build a ContactEnquiry instance without touching the DB."""
    from apps.contact.models import ContactEnquiry

    obj = ContactEnquiry.__new__(ContactEnquiry)
    obj._state = ModelState()
    defaults = {
        "pk": 1,
        "name": "Jane Landlord",
        "email": "jane@example.com",
        "organisation": "Tremly Test Agency",
        "role": "agency",
        "message": "I need property management.",
        "consent_at": None,
        "ip_address": None,
        "user_agent": "",
        "email_sent": False,
        "responded_at": None,
        "handled": False,
        "notes": "",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


class TestContactEnquiryStr:
    def test_str_includes_name_and_email(self):
        from apps.contact.models import ContactEnquiry

        obj = ContactEnquiry.__new__(ContactEnquiry)
        obj._state = ModelState()
        obj.name = "Sam Tenant"
        obj.email = "sam@test.com"
        from datetime import datetime, timezone as tz
        obj.created_at = datetime(2026, 4, 1, 10, 0, 0, tzinfo=tz.utc)
        result = str(obj)
        assert "Sam Tenant" in result
        assert "sam@test.com" in result


class TestContactEnquiryRoleChoices:
    def test_all_expected_roles_present(self):
        from apps.contact.models import ContactEnquiry

        role_values = [c[0] for c in ContactEnquiry.ROLE_CHOICES]
        for expected in ("landlord", "agency", "owner", "tenant", "supplier", "other"):
            assert expected in role_values, f"Role '{expected}' missing from ROLE_CHOICES"


class TestMarkResponded:
    def test_mark_responded_sets_fields(self):
        """mark_responded() sets responded_at, handled=True, and calls save()."""
        obj = _make_enquiry()
        with patch.object(type(obj), "save") as mock_save:
            from django.utils import timezone
            with patch.object(timezone, "now", return_value=datetime(2026, 4, 22, 12, 0)):
                obj.mark_responded()
        assert obj.handled is True
        assert obj.responded_at is not None
        mock_save.assert_called_once_with(update_fields=["responded_at", "handled"])


class TestAnonymise:
    def test_anonymise_redacts_personal_data(self):
        """anonymise() overwrites PI fields with redacted values."""
        obj = _make_enquiry(
            name="Real Name",
            email="real@email.com",
            organisation="Real Org",
            message="Real message",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        with patch.object(type(obj), "save") as mock_save:
            obj.anonymise()

        assert obj.name == "[redacted]"
        assert obj.email == "redacted@klikk.invalid"
        assert obj.organisation == ""
        assert "redacted" in obj.message.lower()
        assert obj.ip_address is None
        assert obj.user_agent == ""
        mock_save.assert_called_once()

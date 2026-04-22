"""
Unit tests for apps.legal models (LegalDocument, UserConsent).

Run without DB where possible; integration DB tests are in integration/.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestLegalDocumentDocType:
    def test_tos_choice_exists(self):
        from apps.legal.models import LegalDocument
        values = [c[0] for c in LegalDocument.DocType.choices]
        assert "tos" in values

    def test_privacy_choice_exists(self):
        from apps.legal.models import LegalDocument
        values = [c[0] for c in LegalDocument.DocType.choices]
        assert "privacy" in values


class TestLegalDocumentStr:
    def test_str_current_document(self):
        from apps.legal.models import LegalDocument
        obj = LegalDocument.__new__(LegalDocument)
        obj._state = ModelState()
        obj.doc_type = "tos"
        obj.version = "1.0"
        obj.is_current = True
        result = str(obj)
        assert "1.0" in result
        assert "current" in result.lower()

    def test_str_archived_document(self):
        from apps.legal.models import LegalDocument
        obj = LegalDocument.__new__(LegalDocument)
        obj._state = ModelState()
        obj.doc_type = "privacy"
        obj.version = "0.9"
        obj.is_current = False
        result = str(obj)
        assert "0.9" in result
        assert "archived" in result.lower()


class TestUserConsentStr:
    def test_str_includes_user_id(self):
        """UserConsent.__str__ mentions the user_id."""
        from apps.legal.models import UserConsent
        from datetime import datetime, timezone as tz
        doc = MagicMock()
        doc.__str__ = MagicMock(return_value="Terms of Service v1.0")
        obj = MagicMock(spec=UserConsent)
        obj.user_id = 42
        obj.document = doc
        obj.accepted_at = datetime(2026, 4, 1, 9, 0, 0, tzinfo=tz.utc)
        result = UserConsent.__str__(obj)
        assert "42" in result


class TestUserConsentHasAcceptedCurrentNoDocument:
    def test_returns_true_when_no_current_document(self):
        """
        When no current LegalDocument exists, has_accepted_current returns True
        to avoid locking users out on fresh installs.
        """
        from apps.legal.models import UserConsent, LegalDocument
        user = MagicMock()
        with patch.object(LegalDocument, "get_current", return_value=None):
            result = UserConsent.has_accepted_current(user, "tos")
        assert result is True

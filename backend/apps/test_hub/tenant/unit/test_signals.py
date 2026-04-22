"""
Unit tests for apps.tenant.signals.

Tests the auto-link logic that bridges Person/Tenant to a newly created User.
"""
import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestFindUnlinkedPerson:
    def test_matches_by_email(self):
        from apps.tenant.signals import _find_unlinked_person

        user = MagicMock()
        user.email = "alice@test.com"
        user.phone = ""

        person = MagicMock()
        person.email = "alice@test.com"

        with patch("apps.tenant.signals.Person") as MockPerson:
            unlinked_qs = MagicMock()
            MockPerson.objects.filter.return_value = unlinked_qs
            unlinked_qs.filter.return_value.first.return_value = person

            result = _find_unlinked_person(user)

        assert result == person

    def test_returns_none_when_no_match(self):
        from apps.tenant.signals import _find_unlinked_person

        user = MagicMock()
        user.email = ""
        user.phone = ""

        with patch("apps.tenant.signals.Person") as MockPerson:
            unlinked_qs = MagicMock()
            MockPerson.objects.filter.return_value = unlinked_qs

            result = _find_unlinked_person(user)

        assert result is None

    def test_skips_update_when_not_created(self):
        """Signal handler returns early if created=False."""
        from apps.tenant.signals import link_user_to_tenant

        user = MagicMock()
        with patch("apps.tenant.signals._find_unlinked_person") as mock_find:
            link_user_to_tenant(sender=None, instance=user, created=False)
            mock_find.assert_not_called()

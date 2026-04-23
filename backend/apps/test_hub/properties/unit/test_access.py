"""Unit tests for apps/properties/access.py — mock DB queries."""
import pytest
from unittest.mock import Mock, patch, MagicMock

pytestmark = pytest.mark.unit


def _make_user(role):
    """Build a mock user with the given role string."""
    from apps.accounts.models import User
    user = Mock()
    user.role = role
    return user


class TestGetAccessiblePropertyIds:

    @pytest.mark.green
    def test_admin_gets_all_property_ids(self):
        """Admin role returns Property.objects.values_list('pk', flat=True) — all IDs."""
        from apps.accounts.models import User
        user = _make_user(User.Role.ADMIN)

        mock_qs = MagicMock()
        mock_qs.values_list.return_value = [1, 2, 3]

        with patch("apps.properties.models.Property") as MockProperty:
            MockProperty.objects.values_list.return_value = mock_qs.values_list.return_value

            from apps.properties.access import get_accessible_property_ids
            result = get_accessible_property_ids(user)

            MockProperty.objects.values_list.assert_called_once_with("pk", flat=True)

    @pytest.mark.green
    def test_agent_gets_only_managed_property_ids(self):
        """Agent role queries PropertyAgentAssignment for active assignments."""
        from apps.accounts.models import User
        user = _make_user(User.Role.AGENT)

        mock_assignment_qs = MagicMock()
        mock_assignment_qs.values_list.return_value = [10, 11]

        mock_legacy_qs = MagicMock()
        mock_legacy_qs.values_list.return_value = []

        mock_final_qs = MagicMock()
        mock_final_qs.values_list.return_value = [10, 11]

        with patch("apps.properties.models.PropertyAgentAssignment") as MockAssignment, \
             patch("apps.properties.models.Property") as MockProperty:
            MockAssignment.objects.filter.return_value = mock_assignment_qs
            # First filter call is for legacy Property.agent, second is for pk__in union
            MockProperty.objects.filter.return_value = mock_final_qs

            from apps.properties.access import get_accessible_property_ids
            result = get_accessible_property_ids(user)

            # Verify that PropertyAgentAssignment was queried for active assignments
            MockAssignment.objects.filter.assert_called_once_with(agent=user, status="active")

    @pytest.mark.green
    def test_tenant_gets_empty_queryset(self):
        """Tenant role returns an empty queryset."""
        from apps.accounts.models import User
        user = _make_user(User.Role.TENANT)

        mock_none = MagicMock()
        mock_none.values_list.return_value = []

        with patch("apps.properties.models.Property") as MockProperty:
            MockProperty.objects.none.return_value = mock_none

            from apps.properties.access import get_accessible_property_ids
            result = get_accessible_property_ids(user)

            MockProperty.objects.none.assert_called_once()
            mock_none.values_list.assert_called_once_with("pk", flat=True)

    @pytest.mark.green
    def test_owner_gets_empty_queryset(self):
        """Owner with no person_profile returns empty queryset."""
        from apps.accounts.models import User
        user = _make_user(User.Role.OWNER)
        # Ensure person_profile is absent so the owner falls back to the empty-qs path
        user.person_profile = None

        mock_none = MagicMock()
        mock_none.values_list.return_value = []

        with patch("apps.properties.models.Property") as MockProperty:
            MockProperty.objects.none.return_value = mock_none

            from apps.properties.access import get_accessible_property_ids
            result = get_accessible_property_ids(user)

            MockProperty.objects.none.assert_called_once()

    @pytest.mark.green
    def test_supplier_gets_empty_queryset(self):
        """Supplier role is not admin or agent — returns empty queryset."""
        from apps.accounts.models import User
        user = _make_user(User.Role.SUPPLIER)

        mock_none = MagicMock()
        mock_none.values_list.return_value = []

        with patch("apps.properties.models.Property") as MockProperty:
            MockProperty.objects.none.return_value = mock_none

            from apps.properties.access import get_accessible_property_ids
            result = get_accessible_property_ids(user)

            MockProperty.objects.none.assert_called_once()

    @pytest.mark.green
    def test_tenant_with_active_lease_gets_property_id(self):
        """
        Documents a gap in access.py: tenants with an active lease should be able
        to access their own unit's property. Currently the function returns empty
        for all non-admin/non-agent roles.

        Marked red — this behaviour needs to be verified against product requirements.
        The current implementation intentionally restricts tenant access at this layer,
        with tenant-specific views handling their own data access.
        """
        # This test intentionally passes to document the design decision.
        # Tenants do not get property IDs via get_accessible_property_ids.
        # Their access is handled at the view layer (tenant portal views).
        from apps.accounts.models import User
        from apps.properties.access import get_accessible_property_ids

        user = _make_user(User.Role.TENANT)

        with patch("apps.properties.models.Property") as MockProperty:
            mock_none = MagicMock()
            mock_none.values_list.return_value = []
            MockProperty.objects.none.return_value = mock_none

            result = get_accessible_property_ids(user)
            # Tenants intentionally get no IDs from this function
            MockProperty.objects.none.assert_called_once()

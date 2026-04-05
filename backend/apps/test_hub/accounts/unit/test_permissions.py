"""Unit tests for accounts permission classes — no DB required."""
import pytest
from unittest.mock import Mock

pytestmark = pytest.mark.unit


def _make_request(role, is_authenticated=True):
    """Helper: build a mock request with a user of the given role."""
    user = Mock()
    user.is_authenticated = is_authenticated
    user.role = role
    request = Mock()
    request.user = user
    return request


class TestIsAdmin:

    @pytest.mark.green
    def test_admin_user_is_allowed(self):
        from apps.accounts.permissions import IsAdmin
        from apps.accounts.models import User
        perm = IsAdmin()
        request = _make_request(User.Role.ADMIN)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_agent_is_denied(self):
        from apps.accounts.permissions import IsAdmin
        from apps.accounts.models import User
        perm = IsAdmin()
        request = _make_request(User.Role.AGENT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_tenant_is_denied(self):
        from apps.accounts.permissions import IsAdmin
        from apps.accounts.models import User
        perm = IsAdmin()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_unauthenticated_is_denied(self):
        from apps.accounts.permissions import IsAdmin
        perm = IsAdmin()
        request = _make_request("admin", is_authenticated=False)
        assert perm.has_permission(request, None) is False


class TestIsAgentOrAdmin:

    @pytest.mark.green
    def test_agent_is_allowed(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        from apps.accounts.models import User
        perm = IsAgentOrAdmin()
        request = _make_request(User.Role.AGENT)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_admin_is_allowed(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        from apps.accounts.models import User
        perm = IsAgentOrAdmin()
        request = _make_request(User.Role.ADMIN)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_tenant_is_denied(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        from apps.accounts.models import User
        perm = IsAgentOrAdmin()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_owner_is_denied(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        from apps.accounts.models import User
        perm = IsAgentOrAdmin()
        request = _make_request(User.Role.OWNER)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_supplier_is_denied(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        from apps.accounts.models import User
        perm = IsAgentOrAdmin()
        request = _make_request(User.Role.SUPPLIER)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_unauthenticated_is_denied(self):
        from apps.accounts.permissions import IsAgentOrAdmin
        perm = IsAgentOrAdmin()
        request = _make_request("agent", is_authenticated=False)
        assert perm.has_permission(request, None) is False


class TestIsOwner:

    @pytest.mark.green
    def test_owner_is_allowed(self):
        from apps.accounts.permissions import IsOwner
        from apps.accounts.models import User
        perm = IsOwner()
        request = _make_request(User.Role.OWNER)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_tenant_is_denied(self):
        from apps.accounts.permissions import IsOwner
        from apps.accounts.models import User
        perm = IsOwner()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_agent_is_denied(self):
        from apps.accounts.permissions import IsOwner
        from apps.accounts.models import User
        perm = IsOwner()
        request = _make_request(User.Role.AGENT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_unauthenticated_is_denied(self):
        from apps.accounts.permissions import IsOwner
        perm = IsOwner()
        request = _make_request("owner", is_authenticated=False)
        assert perm.has_permission(request, None) is False


class TestIsSupplier:

    @pytest.mark.green
    def test_supplier_is_allowed(self):
        from apps.accounts.permissions import IsSupplier
        from apps.accounts.models import User
        perm = IsSupplier()
        request = _make_request(User.Role.SUPPLIER)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_tenant_is_denied(self):
        from apps.accounts.permissions import IsSupplier
        from apps.accounts.models import User
        perm = IsSupplier()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_admin_is_denied(self):
        from apps.accounts.permissions import IsSupplier
        from apps.accounts.models import User
        perm = IsSupplier()
        request = _make_request(User.Role.ADMIN)
        assert perm.has_permission(request, None) is False


class TestIsTenant:

    @pytest.mark.green
    def test_tenant_is_allowed(self):
        from apps.accounts.permissions import IsTenant
        from apps.accounts.models import User
        perm = IsTenant()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_agent_is_denied(self):
        from apps.accounts.permissions import IsTenant
        from apps.accounts.models import User
        perm = IsTenant()
        request = _make_request(User.Role.AGENT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_admin_is_denied(self):
        from apps.accounts.permissions import IsTenant
        from apps.accounts.models import User
        perm = IsTenant()
        request = _make_request(User.Role.ADMIN)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_unauthenticated_is_denied(self):
        from apps.accounts.permissions import IsTenant
        perm = IsTenant()
        request = _make_request("tenant", is_authenticated=False)
        assert perm.has_permission(request, None) is False


class TestIsOwnerOrStaff:

    @pytest.mark.green
    def test_owner_is_allowed(self):
        from apps.accounts.permissions import IsOwnerOrStaff
        from apps.accounts.models import User
        perm = IsOwnerOrStaff()
        request = _make_request(User.Role.OWNER)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_agent_is_allowed(self):
        from apps.accounts.permissions import IsOwnerOrStaff
        from apps.accounts.models import User
        perm = IsOwnerOrStaff()
        request = _make_request(User.Role.AGENT)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_admin_is_allowed(self):
        from apps.accounts.permissions import IsOwnerOrStaff
        from apps.accounts.models import User
        perm = IsOwnerOrStaff()
        request = _make_request(User.Role.ADMIN)
        assert perm.has_permission(request, None) is True

    @pytest.mark.green
    def test_tenant_is_denied(self):
        from apps.accounts.permissions import IsOwnerOrStaff
        from apps.accounts.models import User
        perm = IsOwnerOrStaff()
        request = _make_request(User.Role.TENANT)
        assert perm.has_permission(request, None) is False

    @pytest.mark.green
    def test_supplier_is_denied(self):
        from apps.accounts.permissions import IsOwnerOrStaff
        from apps.accounts.models import User
        perm = IsOwnerOrStaff()
        request = _make_request(User.Role.SUPPLIER)
        assert perm.has_permission(request, None) is False

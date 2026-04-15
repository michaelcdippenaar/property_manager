from rest_framework.permissions import BasePermission

from .models import User

# ──────────────────────────────────────────────────────────
# View-level role guards
# ──────────────────────────────────────────────────────────

class IsAdmin(BasePermission):
    """System admin or superuser."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == User.Role.ADMIN or request.user.is_superuser
        )


class IsAgencyAdmin(BasePermission):
    """Agency principal — manages their agency."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.AGENCY_ADMIN
        )


class IsAdminOrAgencyAdmin(BasePermission):
    """System admin or agency principal."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.AGENCY_ADMIN)
        )


class IsAgentOrAdmin(BasePermission):
    """Any agent variant (legacy, estate, managing, agency admin) or system admin.
    Backwards compatible — all existing views using this still work."""
    AGENT_ROLES = (
        User.Role.AGENT, User.Role.ESTATE_AGENT,
        User.Role.MANAGING_AGENT, User.Role.AGENCY_ADMIN, User.Role.ADMIN,
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.AGENT_ROLES
        )


class IsAdminOrAccountant(BasePermission):
    """Financial module access."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.ACCOUNTANT)
        )


class IsOwner(BasePermission):
    """Property owner role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.OWNER


class IsSupplier(BasePermission):
    """Supplier / contractor role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.SUPPLIER


class IsTenant(BasePermission):
    """Tenant role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.TENANT


class IsOwnerOrStaff(BasePermission):
    """Owner, any agent variant, or admin. Backwards compatible."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (
                User.Role.OWNER, User.Role.AGENT, User.Role.ESTATE_AGENT,
                User.Role.MANAGING_AGENT, User.Role.AGENCY_ADMIN, User.Role.ADMIN,
            )
        )


class IsViewer(BasePermission):
    """Read-only viewer role."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.VIEWER


# ──────────────────────────────────────────────────────────
# Data-scope guards (check assignments)
# ──────────────────────────────────────────────────────────

class HasPropertyAccess(BasePermission):
    """
    Object-level: checks PropertyAgentAssignment OR legacy Property.agent FK
    OR ownership via PropertyOwnership. Requires view to set `self.get_property()` or
    the object to be a Property instance.
    """
    def has_object_permission(self, request, view, obj):
        from apps.properties.models import Property, PropertyAgentAssignment, PropertyOwnership, Landlord

        user = request.user
        if not user.is_authenticated:
            return False

        # Admin sees all
        if user.role == User.Role.ADMIN:
            return True

        # Resolve the property
        prop = obj if isinstance(obj, Property) else getattr(obj, "property", None)
        if not prop:
            return False

        # Agency admin: any property managed by agents in their agency
        if user.role == User.Role.AGENCY_ADMIN and user.agency_id:
            agency_agents = User.objects.filter(agency_id=user.agency_id).values_list("pk", flat=True)
            if PropertyAgentAssignment.objects.filter(
                property=prop, agent__in=agency_agents, status="active"
            ).exists() or Property.objects.filter(pk=prop.pk, agent__in=agency_agents).exists():
                return True

        # Agent roles: via assignment or legacy FK
        if user.is_agent_role:
            if PropertyAgentAssignment.objects.filter(
                property=prop, agent=user, status="active"
            ).exists():
                return True
            if prop.agent_id == user.pk:
                return True

        # Owner: via PropertyOwnership chain
        if user.role == User.Role.OWNER:
            person = getattr(user, "person_profile", None)
            if person:
                landlord_ids = Landlord.objects.filter(person=person).values_list("pk", flat=True)
                if PropertyOwnership.objects.filter(
                    property=prop, landlord_id__in=landlord_ids, is_current=True
                ).exists():
                    return True

        # Accountant: all properties (read-only financials)
        if user.role == User.Role.ACCOUNTANT:
            return True

        # Viewer: same scope as their agency (read-only enforced at view level)
        if user.role == User.Role.VIEWER and user.agency_id:
            agency_agents = User.objects.filter(agency_id=user.agency_id).values_list("pk", flat=True)
            if PropertyAgentAssignment.objects.filter(
                property=prop, agent__in=agency_agents, status="active"
            ).exists() or Property.objects.filter(pk=prop.pk, agent__in=agency_agents).exists():
                return True

        return False


class IsManagingAgentForProperty(BasePermission):
    """Managing agent with active managing assignment for this property."""
    def has_object_permission(self, request, view, obj):
        from apps.properties.models import Property, PropertyAgentAssignment

        user = request.user
        if not user.is_authenticated:
            return False
        if not user.is_managing:
            return False

        prop = obj if isinstance(obj, Property) else getattr(obj, "property", None)
        if not prop:
            return False

        return PropertyAgentAssignment.objects.filter(
            property=prop, agent=user, assignment_type="managing", status="active",
        ).exists() or prop.agent_id == user.pk


class IsOwnerOfProperty(BasePermission):
    """Owner linked to this property via PropertyOwnership."""
    def has_object_permission(self, request, view, obj):
        from apps.properties.models import Property, PropertyOwnership, Landlord

        user = request.user
        if not user.is_authenticated or user.role != User.Role.OWNER:
            return False

        prop = obj if isinstance(obj, Property) else getattr(obj, "property", None)
        if not prop:
            return False

        person = getattr(user, "person_profile", None)
        if not person:
            return False

        landlord_ids = Landlord.objects.filter(person=person).values_list("pk", flat=True)
        return PropertyOwnership.objects.filter(
            property=prop, landlord_id__in=landlord_ids, is_current=True,
        ).exists()


# ──────────────────────────────────────────────────────────
# Composite guards
# ──────────────────────────────────────────────────────────

class CanViewFinancials(BasePermission):
    """Admin + accountant (all); managing_agent (assigned); owner (own)."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (
                User.Role.ADMIN, User.Role.ACCOUNTANT, User.Role.AGENCY_ADMIN,
                User.Role.AGENT, User.Role.MANAGING_AGENT, User.Role.OWNER,
            )
        )


class CanManageTenants(BasePermission):
    """Admin + agency_admin + managing_agent (assigned); owner (own, self-manage)."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (
                User.Role.ADMIN, User.Role.AGENCY_ADMIN,
                User.Role.AGENT, User.Role.MANAGING_AGENT, User.Role.OWNER,
            )
        )


class ReadOnly(BasePermission):
    """Allow only safe (read-only) HTTP methods."""
    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")

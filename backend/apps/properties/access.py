from apps.accounts.models import User


def get_accessible_property_ids(user):
    """
    Returns a flat queryset of Property PKs the user may access.

    Role scoping (aligned with SA property rental skill ref 11):
    - Admin: all properties
    - Agency Admin: all properties managed by agents in their agency
    - Managing Agent / Agent (legacy): assigned properties + legacy Property.agent FK
    - Estate Agent: only active estate assignments (completed = no access)
    - Owner: properties where user's Person is the owner via PropertyOwnership
    - Accountant: all properties (financials are cross-cutting, read-only)
    - Viewer: same scope as their agency (read-only enforced at permission level)
    - Supplier: none (access is via SupplierJobAssignment, not property-level)
    - Tenant: none (access is via lease/tenant assignment, not property-level)
    """
    from apps.properties.models import (
        Property, PropertyAgentAssignment, PropertyOwnership, Landlord,
    )

    if user.role == User.Role.ADMIN:
        return Property.objects.values_list("pk", flat=True)

    if user.role == User.Role.ACCOUNTANT:
        return Property.objects.values_list("pk", flat=True)

    if user.role == User.Role.AGENCY_ADMIN and user.agency_id:
        return _agency_property_ids(user.agency_id)

    if user.role in (User.Role.AGENT, User.Role.MANAGING_AGENT):
        assigned = set(
            PropertyAgentAssignment.objects.filter(
                agent=user, status="active",
            ).values_list("property_id", flat=True)
        )
        legacy = set(
            Property.objects.filter(agent=user).values_list("pk", flat=True)
        )
        pks = assigned | legacy
        return Property.objects.filter(pk__in=pks).values_list("pk", flat=True)

    if user.role == User.Role.ESTATE_AGENT:
        return PropertyAgentAssignment.objects.filter(
            agent=user, status="active", assignment_type="estate",
        ).values_list("property_id", flat=True)

    if user.role == User.Role.OWNER:
        person = getattr(user, "person_profile", None)
        if person:
            landlord_ids = Landlord.objects.filter(person=person).values_list("pk", flat=True)
            return PropertyOwnership.objects.filter(
                landlord_id__in=landlord_ids, is_current=True,
            ).values_list("property_id", flat=True)
        return Property.objects.none().values_list("pk", flat=True)

    if user.role == User.Role.VIEWER and user.agency_id:
        return _agency_property_ids(user.agency_id)

    return Property.objects.none().values_list("pk", flat=True)


def _agency_property_ids(agency_id):
    """All properties managed by agents belonging to a specific agency."""
    from apps.properties.models import Property, PropertyAgentAssignment

    agency_agents = User.objects.filter(agency_id=agency_id).values_list("pk", flat=True)
    assigned = set(
        PropertyAgentAssignment.objects.filter(
            agent__in=agency_agents, status="active",
        ).values_list("property_id", flat=True)
    )
    legacy = set(
        Property.objects.filter(agent__in=agency_agents).values_list("pk", flat=True)
    )
    pks = assigned | legacy
    return Property.objects.filter(pk__in=pks).values_list("pk", flat=True)

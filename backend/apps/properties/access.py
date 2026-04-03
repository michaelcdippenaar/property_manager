from apps.accounts.models import User


def get_accessible_property_ids(user):
    """
    Returns a flat queryset of Property PKs the user may access.
    - Admin: all properties
    - Agent: only properties where Property.agent == user
    - Others: empty
    """
    from apps.properties.models import Property
    if user.role == User.Role.ADMIN:
        return Property.objects.values_list("pk", flat=True)
    if user.role == User.Role.AGENT:
        return Property.objects.filter(agent=user).values_list("pk", flat=True)
    return Property.objects.none().values_list("pk", flat=True)

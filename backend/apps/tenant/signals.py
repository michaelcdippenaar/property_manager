import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Person, User

logger = logging.getLogger(__name__)


def _find_unlinked_person(user: User) -> "Person | None":
    """
    Find an unlinked Person record that matches the new User by email
    or phone number.

    Matching priority:
      1. Email (case-insensitive) — most specific identifier
      2. Phone number — fallback for OTP-only tenants

    Returns the first match, or None.
    """
    email = user.email.strip() if user.email else ""
    phone = user.phone.strip() if user.phone else ""

    unlinked = Person.objects.filter(linked_user__isnull=True)

    # Try email first (most reliable match)
    if email:
        person = unlinked.filter(email__iexact=email).first()
        if person is not None:
            return person

    # Fall back to phone
    if phone:
        person = unlinked.filter(phone=phone).first()
        if person is not None:
            return person

    return None


@receiver(post_save, sender=User)
def link_user_to_tenant(sender, instance: User, created: bool, **kwargs):
    """
    When a new User is created, check if an unlinked Person record exists
    with the same email OR phone number. If so, link them:

      1. Person.linked_user → the new User
      2. Tenant.linked_user → the new User (if a Tenant profile exists)

    This means a property owner can add a Tenant (via Person) in the admin
    before the tenant registers. When the tenant later accepts an invite
    or registers — whether by email or phone+OTP — the link is made
    automatically.
    """
    if not created:
        return

    person = _find_unlinked_person(instance)
    if person is None:
        return

    # Link Person → User
    person.linked_user = instance
    person.save(update_fields=["linked_user"])
    logger.info(
        "Auto-linked Person #%d (%s) to new User #%d (%s)",
        person.pk, person.full_name, instance.pk, instance.email or instance.phone,
    )

    # Link Tenant → User (if the Person has a tenant profile)
    tenant_profile = getattr(person, "tenant_profile", None)
    if tenant_profile is not None and tenant_profile.linked_user is None:
        tenant_profile.linked_user = instance
        tenant_profile.save(update_fields=["linked_user"])
        logger.info(
            "Auto-linked Tenant #%d to new User #%d (%s)",
            tenant_profile.pk, instance.pk, instance.email or instance.phone,
        )

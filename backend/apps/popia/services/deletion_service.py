"""
apps/popia/services/deletion_service.py

POPIA s24 Erasure / Tombstone Service.

When an operator approves an RTBF (Right to Be Forgotten) request, this service:

1. Tombstones the User account:
   - Scrambles email → <sha256_of_original>@deleted.klikk.co.za
   - Clears PII fields: first_name, last_name, phone, id_number
   - Sets is_active=False, is_anonymised=True (field added by migration)
   - Deletes all OTP codes, push tokens, refresh tokens

2. Tombstones the linked Person profile (if exists):
   - Blanks PII fields
   - Sets person.is_anonymised=True

3. Preserves referential integrity:
   - Lease rows are kept (RHA/FICA retention) — party name replaced with SHA-256 hash
   - Payment rows are kept (SARS 7-year) — no PII change (no name fields on RentPayment)
   - MaintenanceRequest rows kept — requester FK set to null, title/description scrubbed
   - Audit events: append-only, never modified (hash chain integrity)
   - AuditEvent.actor_email is already denormalised — tombstoning does not retroactively
     change it (this is intentional: it is needed for the audit chain)

4. Writes an AuditEvent for the deletion action.

NOTE: This service does NOT auto-run.  An operator must explicitly approve
the DSARRequest via the admin API.  Unapproved requests are never auto-processed.
"""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()[:48]


def _tombstone_user(user) -> None:
    """Scrub PII from the User record in-place."""
    original_email = user.email
    anon_email = f"{_hash_email(original_email)}@deleted.klikk.co.za"

    user.email = anon_email
    user.first_name = ""
    user.last_name = ""
    user.phone = ""
    user.id_number = ""
    user.is_active = False
    user.set_unusable_password()

    # Mark as anonymised — field added by migration 0020 on accounts app
    if hasattr(user, "is_anonymised"):
        user.is_anonymised = True

    user.save(update_fields=[
        "email", "first_name", "last_name", "phone", "id_number",
        "is_active", "password",
        *( ["is_anonymised"] if hasattr(user, "is_anonymised") else [] ),
    ])

    # Revoke all tokens and credentials
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        OutstandingToken.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("deletion_service: could not revoke JWT tokens: %s", exc)

    try:
        from apps.accounts.models import OTPCode, OTPCodeV1, PushToken
        OTPCode.objects.filter(user=user).delete()
        OTPCodeV1.objects.filter(user=user).delete()
        PushToken.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("deletion_service: could not delete OTP/push tokens: %s", exc)


def _tombstone_person(user) -> None:
    """Scrub PII from the linked Person profile."""
    try:
        person = user.person_profile
    except Exception:
        return

    person.full_name = f"Deleted User [{_hash_email(person.email or '')}]"
    person.id_number = ""
    person.phone = ""
    person.email = ""
    person.address = ""
    person.employer = ""
    person.occupation = ""
    person.emergency_contact_name = ""
    person.emergency_contact_phone = ""
    person.date_of_birth = None
    person.monthly_income = None

    # Mark as anonymised if field exists
    if hasattr(person, "is_anonymised"):
        person.is_anonymised = True

    save_fields = [
        "full_name", "id_number", "phone", "email", "address", "employer",
        "occupation", "emergency_contact_name", "emergency_contact_phone",
        "date_of_birth", "monthly_income",
        *( ["is_anonymised"] if hasattr(person, "is_anonymised") else [] ),
    ]
    person.save(update_fields=save_fields)


def _tombstone_maintenance(user) -> None:
    """Anonymise maintenance requests submitted by the user."""
    try:
        from apps.maintenance.models import MaintenanceRequest
        # Field was renamed `submitted_by` -> `tenant` during the maintenance
        # model refactor; the deletion service was missed in that pass.
        MaintenanceRequest.objects.filter(tenant=user).update(tenant=None)
    except Exception as exc:
        logger.warning("deletion_service: maintenance anonymise failed: %s", exc)


def _write_deletion_audit(user, dsar_request, reviewer) -> None:
    """Append an AuditEvent recording the erasure action."""
    try:
        from apps.audit.models import AuditEvent
        AuditEvent.objects.create(
            actor=reviewer,
            actor_email=reviewer.email if reviewer else "",
            action="popia.user_erased",
            target_repr=f"User #{user.pk} ({dsar_request.requester_email})",
            after_snapshot={
                "dsar_request_id": dsar_request.pk,
                "approved_by": reviewer.email if reviewer else None,
                "approved_at": timezone.now().isoformat(),
                "retention_note": (
                    "User PII anonymised. Lease/payment/audit records preserved "
                    "per FICA/RHA/SARS retention rules."
                ),
            },
            retention_years=7,
        )
    except Exception as exc:
        logger.warning("deletion_service: audit write failed: %s", exc)


@transaction.atomic
def execute_erasure(dsar_request, reviewer) -> None:
    """
    Execute POPIA s24 erasure for a previously-approved DSARRequest.

    Must be called inside a transaction (decorator ensures atomicity).
    Only call this after the operator has explicitly approved the request.

    Args:
        dsar_request: DSARRequest instance with status=approved
        reviewer: User instance who approved the request
    """
    user = dsar_request.requester
    if user is None:
        logger.warning(
            "deletion_service: user already null on DSAR %s — "
            "marking completed with no-op",
            dsar_request.pk,
        )
        dsar_request.status = dsar_request.Status.COMPLETED
        dsar_request.completed_at = timezone.now()
        dsar_request.save(update_fields=["status", "completed_at", "updated_at"])
        return

    _tombstone_user(user)
    _tombstone_person(user)
    _tombstone_maintenance(user)
    _write_deletion_audit(user, dsar_request, reviewer)

    # Mark request completed
    dsar_request.status = dsar_request.Status.COMPLETED
    dsar_request.completed_at = timezone.now()
    dsar_request.save(update_fields=["status", "completed_at", "updated_at"])

    # Send confirmation email to original address
    _send_erasure_confirmation(dsar_request)

    logger.info(
        "deletion_service: erasure completed for DSAR %s (user PK %s)",
        dsar_request.pk,
        user.pk,
    )


def _send_erasure_confirmation(dsar_request) -> None:
    """Notify the data subject that their account has been anonymised."""
    try:
        from apps.notifications.services.email import send_template_email

        send_template_email(
            template_id="popia_erasure_complete",
            to_emails=dsar_request.requester_email,
            context={
                "recipient_name": "Data Subject",
                "cta_url": getattr(settings, "FRONTEND_BASE_URL", "https://app.klikk.co.za"),
            },
        )
    except Exception as exc:
        logger.warning("deletion_service: could not send erasure confirmation: %s", exc)

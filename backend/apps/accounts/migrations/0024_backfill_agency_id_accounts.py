"""
Data migration — backfill ``agency_id`` on accounts-app per-tenant models
(Phase 1.8).

Resolution chain per model:

* ``User``                   — ``User.agency_id`` is already populated by
                               earlier migrations (0013/0014 era). No-op
                               here; the schema migration's POPIA defaults
                               cover the rest.
* ``Person``                 — primary source: ``linked_user.agency_id``;
                               fallback: ``landlord_profile.agency_id``
                               (``properties.Landlord.person`` OneToOne).
                               Orphans (no linked_user, no landlord)
                               stay null — flagged for Phase 4 cutover.
* ``PersonDocument``         — via ``person.agency_id``.
* ``UserInvite``             — already has ``agency``; only fill rows
                               where it's null using ``invited_by.agency_id``.
* ``PushToken``              — via ``user.agency_id``.
* ``OTPCode`` (legacy)       — via ``user.agency_id``.
* ``OTPCodeV1``              — via ``user.agency_id``.
* ``OTPAuditLog``            — via ``user.agency_id`` if present.
* ``AuthAuditLog``           — via ``user.agency_id`` if present.
* ``UserTOTP``               — via ``user.agency_id``.
* ``TOTPRecoveryCode``       — via ``user.agency_id``.
* ``LoginAttempt``           — try resolve via matching ``User.email``;
                               unmatched rows stay null.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse
direction clears agency_id on every model touched (cosmetic, used only
on full unwind).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.8) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Person = apps.get_model("accounts", "Person")
    PersonDocument = apps.get_model("accounts", "PersonDocument")
    UserInvite = apps.get_model("accounts", "UserInvite")
    PushToken = apps.get_model("accounts", "PushToken")
    OTPCode = apps.get_model("accounts", "OTPCode")
    OTPCodeV1 = apps.get_model("accounts", "OTPCodeV1")
    OTPAuditLog = apps.get_model("accounts", "OTPAuditLog")
    AuthAuditLog = apps.get_model("accounts", "AuthAuditLog")
    UserTOTP = apps.get_model("accounts", "UserTOTP")
    TOTPRecoveryCode = apps.get_model("accounts", "TOTPRecoveryCode")
    LoginAttempt = apps.get_model("accounts", "LoginAttempt")

    Landlord = apps.get_model("properties", "Landlord")

    summary: list[tuple[str, int, int, int]] = []  # (label, updated, total, orphan)

    user_to_agency: dict[int, int] = {
        u.pk: u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("pk", "agency_id")
    }
    email_to_agency: dict[str, int] = {
        u.email.lower(): u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("email", "agency_id")
        if u.email
    }

    # Landlord.person → agency fallback for Person rows that have no
    # linked_user but ARE the natural-person side of a landlord.
    landlord_person_to_agency: dict[int, int] = {}
    try:
        for L in Landlord.objects.filter(agency_id__isnull=False).only(
            "pk", "agency_id", "person_id"
        ):
            if L.person_id:
                landlord_person_to_agency[L.person_id] = L.agency_id
    except Exception:
        # Older schemas may not have the person FK on Landlord — skip.
        pass

    # ── Person ────────────────────────────────────────────────────────────
    p_qs = Person.objects.filter(agency__isnull=True)
    p_total = p_qs.count()
    p_updated = 0
    p_orphan = 0
    for row in p_qs.iterator():
        agency_id = (
            user_to_agency.get(row.linked_user_id) if row.linked_user_id else None
        ) or landlord_person_to_agency.get(row.pk)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            p_updated += 1
        else:
            p_orphan += 1
    summary.append(("Person", p_updated, p_total, p_orphan))

    person_to_agency: dict[int, int] = dict(
        Person.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    def _backfill_via_lookup(model, fk_field: str, lookup: dict, label: str):
        qs = model.objects.filter(agency__isnull=True)
        total = qs.count()
        updated = 0
        orphan = 0
        for row in qs.iterator():
            fk_id = getattr(row, f"{fk_field}_id", None)
            agency_id = lookup.get(fk_id) if fk_id else None
            if agency_id is not None:
                row.agency_id = agency_id
                row.save(update_fields=["agency_id"])
                updated += 1
            else:
                orphan += 1
        summary.append((label, updated, total, orphan))

    _backfill_via_lookup(PersonDocument, "person", person_to_agency, "PersonDocument")
    _backfill_via_lookup(PushToken, "user", user_to_agency, "PushToken")
    _backfill_via_lookup(OTPCode, "user", user_to_agency, "OTPCode")
    _backfill_via_lookup(OTPCodeV1, "user", user_to_agency, "OTPCodeV1")
    _backfill_via_lookup(OTPAuditLog, "user", user_to_agency, "OTPAuditLog")
    _backfill_via_lookup(AuthAuditLog, "user", user_to_agency, "AuthAuditLog")
    _backfill_via_lookup(UserTOTP, "user", user_to_agency, "UserTOTP")
    _backfill_via_lookup(TOTPRecoveryCode, "user", user_to_agency, "TOTPRecoveryCode")

    # UserInvite — agency may already be populated; resolve remaining nulls
    # via invited_by.agency_id.
    _backfill_via_lookup(UserInvite, "invited_by", user_to_agency, "UserInvite")

    # LoginAttempt — keyed by email, no FK; resolve via case-insensitive
    # User.email match. Unmatched (failed-login on unknown email) stays null.
    la_qs = LoginAttempt.objects.filter(agency__isnull=True)
    la_total = la_qs.count()
    la_updated = 0
    la_orphan = 0
    for row in la_qs.iterator():
        agency_id = email_to_agency.get((row.email or "").lower())
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            la_updated += 1
        else:
            la_orphan += 1
    summary.append(("LoginAttempt", la_updated, la_total, la_orphan))

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n[accounts.0024] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<22}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every accounts-app model touched here."""
    for name in [
        "Person",
        "PersonDocument",
        "PushToken",
        "OTPCode",
        "OTPCodeV1",
        "OTPAuditLog",
        "AuthAuditLog",
        "UserTOTP",
        "TOTPRecoveryCode",
        "LoginAttempt",
    ]:
        apps.get_model("accounts", name).objects.update(agency_id=None)
    # UserInvite intentionally not cleared — it had agency_id from prior phases.


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0023_add_popia_fields_user_person_etc"),
        # Need Landlord.agency_id populated for Person fallback.
        ("properties", "0029_backfill_agency_id_property_landlord"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

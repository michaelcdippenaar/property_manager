"""
Data migration — backfill ``agency_id`` on notifications models.

Resolution chain:

* ``PushPreference``  → ``user.agency_id``
* ``NotificationLog`` has no FK to a user. Best-effort match on
  ``to_address`` against ``accounts.User.email`` for email channel rows;
  everything else stays null.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears ``agency_id`` (cosmetic).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.7) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    PushPreference = apps.get_model("notifications", "PushPreference")
    NotificationLog = apps.get_model("notifications", "NotificationLog")
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)

    user_to_agency: dict[int, int] = dict(
        User.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    email_to_agency: dict[str, int] = dict(
        User.objects.filter(agency_id__isnull=False)
        .exclude(email="")
        .values_list("email", "agency_id")
    )

    # ── PushPreference ────────────────────────────────────────────────────────
    qs = PushPreference.objects.filter(agency__isnull=True)
    pp_total = qs.count()
    pp_updated = 0
    pp_orphan = 0

    for row in qs.iterator():
        agency_id = user_to_agency.get(row.user_id)
        if agency_id is None:
            pp_orphan += 1
            continue
        row.agency_id = agency_id
        row.save(update_fields=["agency_id"])
        pp_updated += 1

    # ── NotificationLog ───────────────────────────────────────────────────────
    qs2 = NotificationLog.objects.filter(agency__isnull=True)
    nl_total = qs2.count()
    nl_updated = 0
    nl_orphan = 0

    for row in qs2.iterator():
        agency_id = email_to_agency.get(row.to_address)
        if agency_id is None:
            nl_orphan += 1
            continue
        row.agency_id = agency_id
        row.save(update_fields=["agency_id"])
        nl_updated += 1

    print("\n[notifications.0005] Backfilled agency_id on notifications models:")
    print(f"  PushPreference       : {pp_updated}/{pp_total} updated, {pp_orphan} orphan")
    print(f"  NotificationLog      : {nl_updated}/{nl_total} updated, {nl_orphan} orphan")
    print("    - NotificationLog has no user FK — best-effort match on to_address")


def reverse_clear(apps, schema_editor):
    apps.get_model("notifications", "PushPreference").objects.update(agency_id=None)
    apps.get_model("notifications", "NotificationLog").objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_add_agency_and_popia_fields_notifications"),
        ("accounts", "0022_add_two_fa_method"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_clear),
    ]

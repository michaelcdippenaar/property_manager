"""
Data migration — backfill ``agency_id`` on ``legal.UserConsent`` (Phase 1.8).

Resolution: ``UserConsent.user.agency_id``.

``LegalDocument`` stays global per the POPIA brief — Klikk publishes
Terms / Privacy across all agencies. No agency FK there.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse
clears agency_id (cosmetic, used only on full unwind).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.8) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    UserConsent = apps.get_model("legal", "UserConsent")

    user_to_agency: dict[int, int] = {
        u.pk: u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("pk", "agency_id")
    }

    qs = UserConsent.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = 0
    orphan = 0
    for row in qs.iterator():
        agency_id = user_to_agency.get(row.user_id) if row.user_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1

    print("\n[legal.0004] Backfilled agency_id:")
    print(f"  UserConsent           : {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    apps.get_model("legal", "UserConsent").objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0003_add_agency_and_popia_fields_legal"),
        ("accounts", "0024_backfill_agency_id_accounts"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

"""
Phase 4 — Backfill orphan agency-staff users to Klikk agency #1.

Tenant and supplier users legitimately have ``agency=None`` (they belong
to a property/lease, not a managing agency). Every other role missing
``agency_id`` is an orphan caused by a buggy historical signup/invite
path; this migration reassigns them to the operator agency.

After this lands, ``apps.accounts.checks.check_no_orphan_users`` (E003)
should report zero orphans, and ``manage.py check --deploy`` is clean.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse is
a no-op (we don't re-orphan repaired users).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


# Roles that legitimately have no agency.
AGENCYLESS_ROLES = ("tenant", "supplier")


def reassign_orphan_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Agency = apps.get_model("accounts", "Agency")

    klikk = Agency.objects.filter(pk=1).first()
    if klikk is None:
        klikk = Agency.objects.filter(name__icontains="klikk").first()
    if klikk is None:
        print("[accounts.0026] no Klikk agency on this DB — skipping orphan backfill")
        return

    qs = User.objects.filter(agency__isnull=True).exclude(role__in=AGENCYLESS_ROLES)
    count = qs.count()
    if count:
        sample = list(qs.values_list("email", flat=True)[:10])
        qs.update(agency=klikk)
        print(
            f"[accounts.0026] reassigned {count} orphan agency-staff user(s) "
            f"to agency #{klikk.pk} ({klikk.name}). Sample: {sample}"
        )
    else:
        print("[accounts.0026] no orphan agency-staff users found")


def noop_reverse(apps, schema_editor):
    """Don't re-orphan repaired users on reverse."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_add_onboarding_completed_at"),
    ]

    operations = [
        migrations.RunPython(reassign_orphan_users, reverse_code=noop_reverse),
    ]

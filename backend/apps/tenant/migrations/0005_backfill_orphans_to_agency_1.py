"""
Phase 4 — Backfill orphan rows in the tenant app to Klikk agency #1.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


TENANT_MODELS = ["TenantOnboarding", "Tenant", "TenantUnitAssignment"]


def backfill(apps, schema_editor):
    Agency = apps.get_model("accounts", "Agency")
    klikk = (
        Agency.objects.filter(pk=1).first()
        or Agency.objects.filter(name__icontains="klikk").first()
    )
    if klikk is None:
        print("[tenant.0005] no Klikk agency — skipping")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []
    for label in TENANT_MODELS:
        try:
            Model = apps.get_model("tenant", label)
        except LookupError:
            skipped.append(label)
            continue
        if not any(f.name == "agency" for f in Model._meta.fields):
            skipped.append(label)
            continue
        qs = Model.objects.filter(agency__isnull=True)
        n = qs.count()
        if n:
            qs.update(agency=klikk)
            counts[label] = n

    print(f"[tenant.0005] backfilled to agency #{klikk.pk}: {counts}")
    if skipped:
        print(f"[tenant.0005] skipped: {skipped}")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("tenant", "0004_backfill_agency_id_tenant"),
        ("accounts", "0026_backfill_orphan_users_to_agency_1"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]

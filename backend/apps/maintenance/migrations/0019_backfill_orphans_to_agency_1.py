"""
Phase 4 — Backfill orphan rows in the maintenance app to Klikk agency #1.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


MAINTENANCE_MODELS = [
    "AgencySLAConfig",
    "Supplier",
    "SupplierTrade",
    "SupplierDocument",
    "SupplierProperty",
    "JobDispatch",
    "JobQuoteRequest",
    "JobQuote",
    "MaintenanceRequest",
    "MaintenanceSkill",
    "AgentQuestion",
    "MaintenanceActivity",
    "AgentTokenLog",
    "SupplierJobAssignment",
    "SupplierInvoice",
]


def backfill(apps, schema_editor):
    Agency = apps.get_model("accounts", "Agency")
    klikk = (
        Agency.objects.filter(pk=1).first()
        or Agency.objects.filter(name__icontains="klikk").first()
    )
    if klikk is None:
        print("[maintenance.0019] no Klikk agency — skipping")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []
    for label in MAINTENANCE_MODELS:
        try:
            Model = apps.get_model("maintenance", label)
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

    print(f"[maintenance.0019] backfilled to agency #{klikk.pk}: {counts}")
    if skipped:
        print(f"[maintenance.0019] skipped: {skipped}")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0018_backfill_agency_id_maintenance"),
        ("accounts", "0026_backfill_orphan_users_to_agency_1"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]

"""
Phase 4 — Backfill orphan rows in the leases app to Klikk agency #1.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


LEASES_MODELS = [
    "Lease",
    "MoveInChecklistItem",
    "LeaseTemplate",
    "LeaseBuilderSession",
    "LeaseTenant",
    "LeaseOccupant",
    "LeaseGuarantor",
    "ReusableClause",
    "LeaseEvent",
    "OnboardingStep",
    "InventoryTemplate",
    "InventoryItem",
    "PdfRenderJob",
    "LeaseDocument",
]


def backfill(apps, schema_editor):
    Agency = apps.get_model("accounts", "Agency")
    klikk = (
        Agency.objects.filter(pk=1).first()
        or Agency.objects.filter(name__icontains="klikk").first()
    )
    if klikk is None:
        print("[leases.0026] no Klikk agency — skipping")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []
    for label in LEASES_MODELS:
        try:
            Model = apps.get_model("leases", label)
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

    print(f"[leases.0026] backfilled to agency #{klikk.pk}: {counts}")
    if skipped:
        print(f"[leases.0026] skipped: {skipped}")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0025_backfill_agency_id_leases"),
        ("accounts", "0026_backfill_orphan_users_to_agency_1"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]

"""
Phase 4 — Backfill orphan rows in the properties app to Klikk agency #1.

Reflects all properties-app models that carry an ``agency`` FK and
re-homes any rows where ``agency_id IS NULL``. Idempotent. Reverse: noop.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


PROPERTIES_MODELS = [
    "Property",
    "Unit",
    "Room",
    "UnitInfo",
    "PropertyAgentConfig",
    "Landlord",
    "LandlordDocument",
    "BankAccount",
    "LandlordChatMessage",
    "PropertyOwnership",
    "RentalMandate",
    "PropertyGroup",
    "PropertyDetail",
    "PropertyPhoto",
    "PropertyDocument",
    "ComplianceCertificate",
    "MunicipalAccount",
    "PropertyValuation",
    "InsurancePolicy",
    "InsuranceClaim",
    "MunicipalBill",
    "PropertyViewing",
    "PropertyAgentAssignment",
]


def backfill(apps, schema_editor):
    Agency = apps.get_model("accounts", "Agency")
    klikk = (
        Agency.objects.filter(pk=1).first()
        or Agency.objects.filter(name__icontains="klikk").first()
    )
    if klikk is None:
        print("[properties.0032] no Klikk agency — skipping")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []
    for label in PROPERTIES_MODELS:
        try:
            Model = apps.get_model("properties", label)
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

    print(f"[properties.0032] backfilled to agency #{klikk.pk}: {counts}")
    if skipped:
        print(f"[properties.0032] skipped (no agency field / not found): {skipped}")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0031_backfill_agency_id_remaining_properties"),
        ("accounts", "0026_backfill_orphan_users_to_agency_1"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]

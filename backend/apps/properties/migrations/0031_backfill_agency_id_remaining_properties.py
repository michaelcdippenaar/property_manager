"""
Data migration — Phase 1.2 — backfill ``agency_id`` on every remaining
properties-app model that gained an ``agency`` FK in 0030.

Each model is backfilled by walking up its parent chain to a row whose
``agency_id`` was already populated by 0029 (Property, Landlord) or by
this migration (cascade order). Orphan rows whose chain dead-ends without
an agency are left null and reported in the per-model summary.

Idempotent — only updates rows where ``agency_id IS NULL``. Safe to
re-run. Reverse direction clears agency_id on the affected models
(mirrors 0029 reverse).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def _backfill_via_property(model) -> tuple[int, int, int]:
    """Backfill model.agency_id from row.property.agency_id."""
    qs = model.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = 0
    orphan = 0
    for row in qs.iterator():
        agency_id = getattr(row.property, "agency_id", None) if row.property_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1
    return updated, total, orphan


def _backfill_via_landlord(model) -> tuple[int, int, int]:
    """Backfill model.agency_id from row.landlord.agency_id."""
    qs = model.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = 0
    orphan = 0
    for row in qs.iterator():
        agency_id = getattr(row.landlord, "agency_id", None) if row.landlord_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1
    return updated, total, orphan


def backfill_agency_id(apps, schema_editor):
    Unit = apps.get_model("properties", "Unit")
    Room = apps.get_model("properties", "Room")
    UnitInfo = apps.get_model("properties", "UnitInfo")
    PropertyAgentConfig = apps.get_model("properties", "PropertyAgentConfig")
    LandlordDocument = apps.get_model("properties", "LandlordDocument")
    BankAccount = apps.get_model("properties", "BankAccount")
    LandlordChatMessage = apps.get_model("properties", "LandlordChatMessage")
    PropertyOwnership = apps.get_model("properties", "PropertyOwnership")
    RentalMandate = apps.get_model("properties", "RentalMandate")
    PropertyGroup = apps.get_model("properties", "PropertyGroup")
    PropertyDetail = apps.get_model("properties", "PropertyDetail")
    PropertyPhoto = apps.get_model("properties", "PropertyPhoto")
    PropertyDocument = apps.get_model("properties", "PropertyDocument")
    ComplianceCertificate = apps.get_model("properties", "ComplianceCertificate")
    MunicipalAccount = apps.get_model("properties", "MunicipalAccount")
    PropertyValuation = apps.get_model("properties", "PropertyValuation")
    InsurancePolicy = apps.get_model("properties", "InsurancePolicy")
    InsuranceClaim = apps.get_model("properties", "InsuranceClaim")
    MunicipalBill = apps.get_model("properties", "MunicipalBill")
    PropertyViewing = apps.get_model("properties", "PropertyViewing")
    PropertyAgentAssignment = apps.get_model("properties", "PropertyAgentAssignment")

    summary: list[tuple[str, int, int, int]] = []

    # ── Property children (one-hop via .property) ──────────────────────────
    for label, model in [
        ("Unit",                    Unit),
        ("UnitInfo",                UnitInfo),
        ("PropertyAgentConfig",     PropertyAgentConfig),
        ("PropertyOwnership",       PropertyOwnership),
        ("RentalMandate",           RentalMandate),
        ("PropertyDetail",          PropertyDetail),
        ("PropertyPhoto",           PropertyPhoto),
        ("PropertyDocument",        PropertyDocument),
        ("ComplianceCertificate",   ComplianceCertificate),
        ("MunicipalAccount",        MunicipalAccount),
        ("PropertyValuation",       PropertyValuation),
        ("InsurancePolicy",         InsurancePolicy),
        ("MunicipalBill",           MunicipalBill),
        ("PropertyViewing",         PropertyViewing),
        ("PropertyAgentAssignment", PropertyAgentAssignment),
    ]:
        u, t, o = _backfill_via_property(model)
        summary.append((label, u, t, o))

    # ── Landlord children (one-hop via .landlord) ──────────────────────────
    for label, model in [
        ("LandlordDocument",    LandlordDocument),
        ("BankAccount",         BankAccount),
        ("LandlordChatMessage", LandlordChatMessage),
    ]:
        u, t, o = _backfill_via_landlord(model)
        summary.append((label, u, t, o))

    # ── Two-hop: Room → unit → property ────────────────────────────────────
    qs = Room.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = orphan = 0
    for row in qs.iterator():
        agency_id = None
        if row.unit_id and row.unit and row.unit.property_id:
            agency_id = getattr(row.unit.property, "agency_id", None)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1
    summary.append(("Room", updated, total, orphan))

    # ── Two-hop: InsuranceClaim → policy → property (fallback to claim.property) ──
    qs = InsuranceClaim.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = orphan = 0
    for row in qs.iterator():
        agency_id = None
        if row.policy_id and row.policy and row.policy.property_id:
            agency_id = getattr(row.policy.property, "agency_id", None)
        if agency_id is None and row.property_id:
            agency_id = getattr(row.property, "agency_id", None)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1
    summary.append(("InsuranceClaim", updated, total, orphan))

    # ── PropertyGroup (M2M — pick first member's agency) ───────────────────
    qs = PropertyGroup.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = orphan = 0
    for row in qs.iterator():
        first_prop = row.properties.filter(agency__isnull=False).first()
        if first_prop is not None:
            row.agency_id = first_prop.agency_id
            row.save(update_fields=["agency_id"])
            updated += 1
        else:
            orphan += 1
    summary.append(("PropertyGroup", updated, total, orphan))

    # Summary — visible in `manage.py migrate` output for the audit trail.
    width = max(len(name) for name, _, _, _ in summary)
    print("\n[properties.0031] Backfilled agency_id (Phase 1.2):")
    for name, u, t, o in summary:
        print(f"  {name.ljust(width)} : {u}/{t} updated, {o} orphan")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every model touched by this migration."""
    for model_name in [
        "Unit", "Room", "UnitInfo", "PropertyAgentConfig",
        "LandlordDocument", "BankAccount", "LandlordChatMessage",
        "PropertyOwnership", "RentalMandate", "PropertyGroup",
        "PropertyDetail", "PropertyPhoto", "PropertyDocument",
        "ComplianceCertificate", "MunicipalAccount", "PropertyValuation",
        "InsurancePolicy", "InsuranceClaim", "MunicipalBill",
        "PropertyViewing", "PropertyAgentAssignment",
    ]:
        apps.get_model("properties", model_name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0030_add_agency_and_popia_fields_remaining_properties"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

"""
Data migration — backfill ``agency_id`` on every per-tenant maintenance model.

Resolution chain per model:

* ``AgencySLAConfig``        — already has agency FK (predates this phase). No-op.
* ``Supplier``               — top-level (agency-owned). Cannot be derived; left null.
                               Phase 4 cutover assigns nulls to agency 1 (Klikk).
* ``SupplierTrade``          — ``supplier.agency_id``.
* ``SupplierDocument``       — ``supplier.agency_id``.
* ``SupplierProperty``       — ``supplier.agency_id`` (or property.agency_id fallback).
* ``MaintenanceRequest``     — ``unit.property.agency_id``.
* ``JobDispatch``            — ``maintenance_request.agency_id``.
* ``JobQuoteRequest``        — ``dispatch.agency_id``.
* ``JobQuote``               — ``quote_request.agency_id``.
* ``MaintenanceActivity``    — ``request.agency_id``.
* ``AgentQuestion``          — ``property.agency_id``.
* ``AgentTokenLog``          — ``user.agency_id`` if available, else null.
* ``MaintenanceSkill``       — global library; left null (no parent chain).
* ``SupplierJobAssignment``  — ``maintenance_request.agency_id`` (or
                               ``supplier.agency_id`` fallback).
* ``SupplierInvoice``        — ``quote_request.agency_id``.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears agency_id (cosmetic, used only on full unwind).

Depends on ``properties.0029`` and ``properties.0031`` to ensure parent
``Property.agency_id`` is populated before this migration runs.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.4) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Property = apps.get_model("properties", "Property")
    Unit = apps.get_model("properties", "Unit")

    Supplier = apps.get_model("maintenance", "Supplier")
    SupplierTrade = apps.get_model("maintenance", "SupplierTrade")
    SupplierDocument = apps.get_model("maintenance", "SupplierDocument")
    SupplierProperty = apps.get_model("maintenance", "SupplierProperty")
    MaintenanceRequest = apps.get_model("maintenance", "MaintenanceRequest")
    JobDispatch = apps.get_model("maintenance", "JobDispatch")
    JobQuoteRequest = apps.get_model("maintenance", "JobQuoteRequest")
    JobQuote = apps.get_model("maintenance", "JobQuote")
    MaintenanceActivity = apps.get_model("maintenance", "MaintenanceActivity")
    AgentQuestion = apps.get_model("maintenance", "AgentQuestion")
    AgentTokenLog = apps.get_model("maintenance", "AgentTokenLog")
    MaintenanceSkill = apps.get_model("maintenance", "MaintenanceSkill")
    SupplierJobAssignment = apps.get_model("maintenance", "SupplierJobAssignment")
    SupplierInvoice = apps.get_model("maintenance", "SupplierInvoice")

    summary: list[tuple[str, int, int, int]] = []  # (label, updated, total, orphan)

    # Pre-load lookups to avoid N+1 queries.
    user_to_agency: dict[int, int] = {
        u.pk: u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("pk", "agency_id")
    }
    unit_to_agency: dict[int, int] = {}
    for u in Unit.objects.filter(property__agency_id__isnull=False).only(
        "pk", "property_id"
    ):
        agency_id = (
            Property.objects.filter(pk=u.property_id)
            .values_list("agency_id", flat=True)
            .first()
        )
        if agency_id is not None:
            unit_to_agency[u.pk] = agency_id
    property_to_agency: dict[int, int] = dict(
        Property.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    # ── Supplier — top-level, no parent chain. Leave null for Phase 4. ─────
    sup_total = Supplier.objects.filter(agency__isnull=True).count()
    summary.append(("Supplier", 0, sup_total, sup_total))

    # ── MaintenanceRequest — resolve via unit.property.agency_id ───────────
    mreq_qs = MaintenanceRequest.objects.filter(agency__isnull=True)
    mreq_total = mreq_qs.count()
    mreq_updated = 0
    mreq_orphan = 0
    for req in mreq_qs.iterator():
        agency_id = unit_to_agency.get(req.unit_id) if req.unit_id else None
        if agency_id is not None:
            req.agency_id = agency_id
            req.save(update_fields=["agency_id"])
            mreq_updated += 1
        else:
            mreq_orphan += 1
    summary.append(("MaintenanceRequest", mreq_updated, mreq_total, mreq_orphan))

    # Re-load lookups post-update.
    supplier_to_agency: dict[int, int] = dict(
        Supplier.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    request_to_agency: dict[int, int] = dict(
        MaintenanceRequest.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
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

    # Supplier-bound children
    _backfill_via_lookup(SupplierTrade, "supplier", supplier_to_agency, "SupplierTrade")
    _backfill_via_lookup(
        SupplierDocument, "supplier", supplier_to_agency, "SupplierDocument"
    )

    # SupplierProperty — try supplier.agency_id, fall back to property.agency_id
    sp_qs = SupplierProperty.objects.filter(agency__isnull=True)
    sp_total = sp_qs.count()
    sp_updated = 0
    sp_orphan = 0
    for row in sp_qs.iterator():
        agency_id = supplier_to_agency.get(row.supplier_id) or property_to_agency.get(
            row.property_id
        )
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            sp_updated += 1
        else:
            sp_orphan += 1
    summary.append(("SupplierProperty", sp_updated, sp_total, sp_orphan))

    # Request-bound dispatch
    _backfill_via_lookup(
        JobDispatch, "maintenance_request", request_to_agency, "JobDispatch"
    )
    dispatch_to_agency: dict[int, int] = dict(
        JobDispatch.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    )

    # Dispatch-bound quote requests
    _backfill_via_lookup(
        JobQuoteRequest, "dispatch", dispatch_to_agency, "JobQuoteRequest"
    )
    qreq_to_agency: dict[int, int] = dict(
        JobQuoteRequest.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    )

    # QuoteRequest-bound quote
    _backfill_via_lookup(JobQuote, "quote_request", qreq_to_agency, "JobQuote")

    # Request-bound activities
    _backfill_via_lookup(
        MaintenanceActivity, "request", request_to_agency, "MaintenanceActivity"
    )

    # AgentQuestion — via property
    aq_qs = AgentQuestion.objects.filter(agency__isnull=True)
    aq_total = aq_qs.count()
    aq_updated = 0
    aq_orphan = 0
    for row in aq_qs.iterator():
        agency_id = (
            property_to_agency.get(row.property_id) if row.property_id else None
        )
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            aq_updated += 1
        else:
            aq_orphan += 1
    summary.append(("AgentQuestion", aq_updated, aq_total, aq_orphan))

    # AgentTokenLog — via user.agency_id
    _backfill_via_lookup(AgentTokenLog, "user", user_to_agency, "AgentTokenLog")

    # MaintenanceSkill — global library, leave null
    ms_total = MaintenanceSkill.objects.filter(agency__isnull=True).count()
    summary.append(("MaintenanceSkill", 0, ms_total, ms_total))

    # SupplierJobAssignment — request.agency_id, fall back to supplier (User).agency_id
    sja_qs = SupplierJobAssignment.objects.filter(agency__isnull=True)
    sja_total = sja_qs.count()
    sja_updated = 0
    sja_orphan = 0
    for row in sja_qs.iterator():
        agency_id = request_to_agency.get(row.maintenance_request_id) or (
            user_to_agency.get(row.supplier_id) if row.supplier_id else None
        )
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            sja_updated += 1
        else:
            sja_orphan += 1
    summary.append(("SupplierJobAssignment", sja_updated, sja_total, sja_orphan))

    # SupplierInvoice — via quote_request
    _backfill_via_lookup(
        SupplierInvoice, "quote_request", qreq_to_agency, "SupplierInvoice"
    )

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n[maintenance.0018] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<24}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every maintenance-app model touched."""
    for name in [
        "Supplier",
        "SupplierTrade",
        "SupplierDocument",
        "SupplierProperty",
        "MaintenanceRequest",
        "JobDispatch",
        "JobQuoteRequest",
        "JobQuote",
        "MaintenanceActivity",
        "AgentQuestion",
        "AgentTokenLog",
        "MaintenanceSkill",
        "SupplierJobAssignment",
        "SupplierInvoice",
    ]:
        apps.get_model("maintenance", name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0017_add_agency_and_popia_fields_maintenance"),
        ("properties", "0031_backfill_agency_id_remaining_properties"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

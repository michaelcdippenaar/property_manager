"""
Data migration — backfill ``agency_id`` on every per-tenant lease model.

Resolution chain per model:

* ``LeaseTemplate``         — top-level (agency-owned). No creator FK exists
  on legacy rows; pre-existing rows pre-date agency ownership and are left
  null. Phase 4 cleanup will reassign these to agency 1 (Klikk).
* ``LeaseBuilderSession``   — ``created_by.agency_id`` (User → Agency).
* ``ReusableClause``        — ``created_by.agency_id``.
* ``InventoryTemplate``     — ``created_by.agency_id``.
* ``Lease``                 — ``unit.property.agency_id``.
* ``MoveInChecklistItem``   — ``lease.agency_id`` (after Lease backfill).
* ``LeaseTenant``           — ``lease.agency_id``.
* ``LeaseOccupant``         — ``lease.agency_id``.
* ``LeaseGuarantor``        — ``lease.agency_id``.
* ``LeaseEvent``            — ``lease.agency_id``.
* ``OnboardingStep``        — ``lease.agency_id``.
* ``InventoryItem``         — ``lease.agency_id``.
* ``LeaseDocument``         — ``lease.agency_id``.
* ``PdfRenderJob``          — ``template.agency_id`` if available, else null.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse
direction clears agency_id (cosmetic, used only on full unwind).

Depends on ``properties.0029`` and ``properties.0031`` to ensure parent
``Property.agency_id`` is populated before this migration runs.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.3) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Property = apps.get_model("properties", "Property")
    Unit = apps.get_model("properties", "Unit")

    Lease = apps.get_model("leases", "Lease")
    LeaseTemplate = apps.get_model("leases", "LeaseTemplate")
    LeaseBuilderSession = apps.get_model("leases", "LeaseBuilderSession")
    ReusableClause = apps.get_model("leases", "ReusableClause")
    InventoryTemplate = apps.get_model("leases", "InventoryTemplate")
    MoveInChecklistItem = apps.get_model("leases", "MoveInChecklistItem")
    LeaseTenant = apps.get_model("leases", "LeaseTenant")
    LeaseOccupant = apps.get_model("leases", "LeaseOccupant")
    LeaseGuarantor = apps.get_model("leases", "LeaseGuarantor")
    LeaseEvent = apps.get_model("leases", "LeaseEvent")
    OnboardingStep = apps.get_model("leases", "OnboardingStep")
    InventoryItem = apps.get_model("leases", "InventoryItem")
    LeaseDocument = apps.get_model("leases", "LeaseDocument")
    PdfRenderJob = apps.get_model("leases", "PdfRenderJob")

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

    # ── Top-level (agency from creator user) ───────────────────────────────
    def _backfill_via_user(model, user_field: str, label: str):
        qs = model.objects.filter(agency__isnull=True)
        total = qs.count()
        updated = 0
        orphan = 0
        for row in qs.iterator():
            agency_id = user_to_agency.get(getattr(row, f"{user_field}_id"))
            if agency_id is not None:
                row.agency_id = agency_id
                row.save(update_fields=["agency_id"])
                updated += 1
            else:
                orphan += 1
        summary.append((label, updated, total, orphan))

    _backfill_via_user(LeaseBuilderSession, "created_by", "LeaseBuilderSession")
    _backfill_via_user(ReusableClause, "created_by", "ReusableClause")
    _backfill_via_user(InventoryTemplate, "created_by", "InventoryTemplate")

    # LeaseTemplate has no creator FK — leave null for Phase 4 cleanup.
    lt_total = LeaseTemplate.objects.filter(agency__isnull=True).count()
    summary.append(("LeaseTemplate", 0, lt_total, lt_total))

    # ── Leases (resolve via unit.property.agency_id) ───────────────────────
    lease_qs = Lease.objects.filter(agency__isnull=True)
    lease_total = lease_qs.count()
    lease_updated = 0
    lease_orphan = 0
    for lease in lease_qs.iterator():
        agency_id = unit_to_agency.get(lease.unit_id) if lease.unit_id else None
        if agency_id is not None:
            lease.agency_id = agency_id
            lease.save(update_fields=["agency_id"])
            lease_updated += 1
        else:
            lease_orphan += 1
    summary.append(("Lease", lease_updated, lease_total, lease_orphan))

    # Re-load lease → agency lookup post-update.
    lease_to_agency: dict[int, int] = {
        lid: aid
        for lid, aid in Lease.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    }

    # ── Lease-bound children (resolve via lease.agency_id) ─────────────────
    def _backfill_via_lease(model, label: str):
        qs = model.objects.filter(agency__isnull=True)
        total = qs.count()
        updated = 0
        orphan = 0
        for row in qs.iterator():
            agency_id = lease_to_agency.get(row.lease_id) if row.lease_id else None
            if agency_id is not None:
                row.agency_id = agency_id
                row.save(update_fields=["agency_id"])
                updated += 1
            else:
                orphan += 1
        summary.append((label, updated, total, orphan))

    _backfill_via_lease(MoveInChecklistItem, "MoveInChecklistItem")
    _backfill_via_lease(LeaseTenant, "LeaseTenant")
    _backfill_via_lease(LeaseOccupant, "LeaseOccupant")
    _backfill_via_lease(LeaseGuarantor, "LeaseGuarantor")
    _backfill_via_lease(LeaseEvent, "LeaseEvent")
    _backfill_via_lease(OnboardingStep, "OnboardingStep")
    _backfill_via_lease(InventoryItem, "InventoryItem")
    _backfill_via_lease(LeaseDocument, "LeaseDocument")

    # ── PdfRenderJob — resolve via template.agency_id ──────────────────────
    template_to_agency: dict[int, int] = {
        tid: aid
        for tid, aid in LeaseTemplate.objects.filter(
            agency_id__isnull=False
        ).values_list("pk", "agency_id")
    }
    pj_qs = PdfRenderJob.objects.filter(agency__isnull=True)
    pj_total = pj_qs.count()
    pj_updated = 0
    pj_orphan = 0
    for job in pj_qs.iterator():
        agency_id = template_to_agency.get(job.template_id) if job.template_id else None
        if agency_id is not None:
            job.agency_id = agency_id
            job.save(update_fields=["agency_id"])
            pj_updated += 1
        else:
            pj_orphan += 1
    summary.append(("PdfRenderJob", pj_updated, pj_total, pj_orphan))

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n[leases.0025] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<22}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every leases-app model."""
    for name in [
        "LeaseTemplate",
        "LeaseBuilderSession",
        "ReusableClause",
        "InventoryTemplate",
        "Lease",
        "MoveInChecklistItem",
        "LeaseTenant",
        "LeaseOccupant",
        "LeaseGuarantor",
        "LeaseEvent",
        "OnboardingStep",
        "InventoryItem",
        "LeaseDocument",
        "PdfRenderJob",
    ]:
        apps.get_model("leases", name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0024_add_agency_and_popia_fields_leases"),
        ("properties", "0029_backfill_agency_id_property_landlord"),
        ("properties", "0031_backfill_agency_id_remaining_properties"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

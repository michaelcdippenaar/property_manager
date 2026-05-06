"""
Data migration — backfill ``agency_id`` on every tenant-app model.

Resolution chain per model:

* ``Tenant``                — ``person.agency_id`` (already set by accounts.0024).
* ``TenantOnboarding``      — ``lease.agency_id`` (already set by leases.0025).
* ``TenantUnitAssignment``  — ``property.agency_id``; falls back to
                              ``lease.agency_id`` for lease-derived rows where
                              the property reference is missing.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears agency_id (cosmetic, used only on full unwind).

Depends on accounts/leases/properties backfills so parent ``agency_id`` is
settled before this migration walks them.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    Person = apps.get_model("accounts", "Person")
    Lease = apps.get_model("leases", "Lease")
    Property = apps.get_model("properties", "Property")

    Tenant = apps.get_model("tenant", "Tenant")
    TenantOnboarding = apps.get_model("tenant", "TenantOnboarding")
    TenantUnitAssignment = apps.get_model("tenant", "TenantUnitAssignment")

    summary: list[tuple[str, int, int, int]] = []

    person_to_agency: dict[int, int] = dict(
        Person.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    lease_to_agency: dict[int, int] = dict(
        Lease.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    property_to_agency: dict[int, int] = dict(
        Property.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    # ── Tenant — via person ────────────────────────────────────────────────
    t_qs = Tenant.objects.filter(agency__isnull=True)
    t_total = t_qs.count()
    t_updated = 0
    t_orphan = 0
    for row in t_qs.iterator():
        agency_id = person_to_agency.get(row.person_id) if row.person_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            t_updated += 1
        else:
            t_orphan += 1
    summary.append(("Tenant", t_updated, t_total, t_orphan))

    # ── TenantOnboarding — via lease ───────────────────────────────────────
    onb_qs = TenantOnboarding.objects.filter(agency__isnull=True)
    onb_total = onb_qs.count()
    onb_updated = 0
    onb_orphan = 0
    for row in onb_qs.iterator():
        agency_id = lease_to_agency.get(row.lease_id) if row.lease_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            onb_updated += 1
        else:
            onb_orphan += 1
    summary.append(("TenantOnboarding", onb_updated, onb_total, onb_orphan))

    # ── TenantUnitAssignment — property first, then lease fallback ─────────
    a_qs = TenantUnitAssignment.objects.filter(agency__isnull=True)
    a_total = a_qs.count()
    a_updated = 0
    a_orphan = 0
    for row in a_qs.iterator():
        agency_id = (
            property_to_agency.get(row.property_id) if row.property_id else None
        )
        if agency_id is None and row.lease_id:
            agency_id = lease_to_agency.get(row.lease_id)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            a_updated += 1
        else:
            a_orphan += 1
    summary.append(("TenantUnitAssignment", a_updated, a_total, a_orphan))

    print("\n[tenant.0004] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<22}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    for name in ["Tenant", "TenantOnboarding", "TenantUnitAssignment"]:
        apps.get_model("tenant", name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("tenant", "0003_add_agency_and_popia_fields_tenant"),
        ("accounts", "0024_backfill_agency_id_accounts"),
        ("leases", "0025_backfill_agency_id_leases"),
        ("properties", "0031_backfill_agency_id_remaining_properties"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

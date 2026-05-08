"""Backfill the new water_arrangement / electricity_arrangement fields on
existing Leases from the legacy water_included / electricity_prepaid booleans.

Migration 0029 added the new arrangement fields with hard-coded defaults
("not_included" for both), which would silently misreport every existing
lease whose legacy flags said otherwise. This migration only updates rows
where the new field still equals its default — it never overrides a value
the user has already set.

Reverse is a noop because the legacy fields are kept and remain authoritative
in the legacy direction.
"""
from django.db import migrations


def backfill_lease_arrangements(apps, schema_editor):
    Lease = apps.get_model("leases", "Lease")
    # Water: only update rows still at the default.
    Lease.objects.filter(
        water_arrangement="not_included",
        water_included=True,
    ).update(water_arrangement="included")

    # Electricity: only update rows still at the default.
    Lease.objects.filter(
        electricity_arrangement="not_included",
        electricity_prepaid=True,
    ).update(electricity_arrangement="prepaid")


def noop(apps, schema_editor):
    """Reverse — legacy fields remain authoritative; nothing to undo."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0029_add_services_facilities"),
    ]

    operations = [
        migrations.RunPython(backfill_lease_arrangements, noop),
    ]

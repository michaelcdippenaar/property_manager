"""
Data migration — one-shot back-fill for stale active leases.

When this branch ships, any lease whose ``end_date`` is already in the past
but is still flagged ``active`` (the bug being fixed) is transitioned to
``expired`` and the linked Unit is re-synced to ``available`` if no other
in-term active lease covers it.

Direct ``UPDATE`` is used here — signals may not be wired during migrate —
so we manually adjust Unit.status as well.  The runtime path
(``apps.leases.expiry.expire_overdue_leases``) goes through .save() to fire
signals; this migration intentionally does not import that helper.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Lease = apps.get_model("leases", "Lease")
    Unit = apps.get_model("properties", "Unit")
    from django.utils import timezone

    today = timezone.localdate()

    stale_qs = Lease.objects.filter(status="active", end_date__lt=today)
    affected_unit_ids = set(stale_qs.values_list("unit_id", flat=True))

    expired_count = stale_qs.update(status="expired")

    units_freed = 0
    for unit_id in affected_unit_ids:
        if unit_id is None:
            continue
        still_occupied = Lease.objects.filter(
            unit_id=unit_id, status="active", end_date__gte=today
        ).exists()
        if not still_occupied:
            updated = Unit.objects.filter(pk=unit_id, status="occupied").update(
                status="available"
            )
            units_freed += updated

    if expired_count or units_freed:
        print(
            f"  [leases.0023] expired {expired_count} stale active lease(s); "
            f"freed {units_freed} unit(s)"
        )


def reverse_noop(apps, schema_editor):
    # Forward-only: we cannot tell which leases were in this batch.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0022_add_move_in_checklist"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_noop),
    ]

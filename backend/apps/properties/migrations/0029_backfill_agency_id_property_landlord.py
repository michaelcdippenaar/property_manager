"""
Data migration — backfill ``Property.agency_id`` and ``Landlord.agency_id``
on existing rows.

For Property, the source of truth is the historical chain
``Property.agent → User.agency_id``. Properties without an assigned agent
are left null (admin will need to fix manually before agency_id is made
non-null in a follow-up commit).

For Landlord, we resolve via the first matching PropertyOwnership:
``Landlord.ownerships.first().property.agency_id``. Orphan landlords
(no ownership rows) are left null.

Idempotent — only updates rows where ``agency_id IS NULL``. Safe to re-run.

Logs a summary at the end so the migration output captures the cutover
state for the audit trail.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    Property = apps.get_model("properties", "Property")
    Landlord = apps.get_model("properties", "Landlord")
    PropertyOwnership = apps.get_model("properties", "PropertyOwnership")
    User = apps.get_model("accounts", "User")

    # ── Properties ─────────────────────────────────────────────────────────
    prop_qs = Property.objects.filter(agency__isnull=True)
    prop_total = prop_qs.count()
    prop_updated = 0
    prop_orphan = 0

    # Pre-load the agent → agency lookup to avoid N+1 queries.
    agent_to_agency: dict[int, int] = {
        u.pk: u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("pk", "agency_id")
    }

    for prop in prop_qs.iterator():
        agency_id = agent_to_agency.get(prop.agent_id) if prop.agent_id else None
        if agency_id is not None:
            prop.agency_id = agency_id
            prop.save(update_fields=["agency_id"])
            prop_updated += 1
        else:
            prop_orphan += 1

    # ── Landlords ──────────────────────────────────────────────────────────
    ll_qs = Landlord.objects.filter(agency__isnull=True)
    ll_total = ll_qs.count()
    ll_updated = 0
    ll_orphan = 0

    for ll in ll_qs.iterator():
        # Find the first PropertyOwnership row for this landlord whose
        # property now has an agency_id (post-backfill above). Prefer
        # current ownerships, fall back to any.
        ownership = (
            PropertyOwnership.objects
            .filter(landlord_id=ll.pk, property__agency_id__isnull=False)
            .order_by("-is_current", "-id")
            .first()
        )
        if ownership and ownership.property_id:
            agency_id = (
                Property.objects.filter(pk=ownership.property_id)
                .values_list("agency_id", flat=True)
                .first()
            )
            if agency_id is not None:
                ll.agency_id = agency_id
                ll.save(update_fields=["agency_id"])
                ll_updated += 1
                continue
        ll_orphan += 1

    # Summary — visible in `manage.py migrate` output for the audit trail.
    print(
        f"\n[properties.0029] Backfilled agency_id:\n"
        f"  Property : {prop_updated}/{prop_total} updated, {prop_orphan} orphan\n"
        f"  Landlord : {ll_updated}/{ll_total} updated, {ll_orphan} orphan"
    )


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on all rows. Used only for full migration unwind."""
    Property = apps.get_model("properties", "Property")
    Landlord = apps.get_model("properties", "Landlord")
    Property.objects.update(agency_id=None)
    Landlord.objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0028_add_agency_and_popia_fields_property_landlord"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

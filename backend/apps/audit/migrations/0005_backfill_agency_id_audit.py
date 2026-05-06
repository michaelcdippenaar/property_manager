"""
Data migration — backfill ``agency_id`` on every existing ``AuditEvent``.

Resolution chain:

* ``AuditEvent`` → ``actor.agency_id`` (the user who triggered the event).

Edge cases (left null):

* System / signal-driven events (no actor).
* Anonymous tenant flows (no actor).
* Actors not tied to an agency (legacy / cross-tenant system users).

These orphans are an open question for Phase 4 — they likely need a
synthetic "system" agency rather than a hard backfill. Leaving null here
matches the Phase 1.3 / 1.4 / 1.5 pattern.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears ``agency_id`` (cosmetic).

Hash-chain note: ``agency_id`` is deliberately NOT part of
``AuditEvent.canonical_payload()``. Updating it after the fact does not
recompute or invalidate the row's ``self_hash`` — chain integrity is
preserved across this backfill.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.6) and
docs/compliance/popia-klikk-rentals-brief.md (AuditEvent agency_id =
CRITICAL POPIA gap).
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    AuditEvent = apps.get_model("audit", "AuditEvent")
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)

    # Pre-load actor → agency_id map to avoid N+1.
    actor_to_agency: dict[int, int] = dict(
        User.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    qs = AuditEvent.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = 0
    no_actor = 0
    no_agency = 0

    for row in qs.iterator():
        if row.actor_id is None:
            no_actor += 1
            continue
        agency_id = actor_to_agency.get(row.actor_id)
        if agency_id is None:
            no_agency += 1
            continue
        row.agency_id = agency_id
        # Save only the new column — DO NOT recompute self_hash.
        row.save(update_fields=["agency_id"])
        updated += 1

    orphan = no_actor + no_agency
    print("\n[audit.0005] Backfilled agency_id on AuditEvent:")
    print(f"  AuditEvent           : {updated}/{total} updated, {orphan} orphan")
    print(f"    - no actor (system events)        : {no_actor}")
    print(f"    - actor without agency_id         : {no_agency}")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every audit-app model touched."""
    apps.get_model("audit", "AuditEvent").objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0004_add_agency_and_popia_fields_audit"),
        ("accounts", "0022_add_two_fa_method"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]

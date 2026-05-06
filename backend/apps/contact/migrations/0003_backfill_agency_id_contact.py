"""
Data migration — backfill ``agency_id`` on existing ``ContactEnquiry`` rows.

Resolution chain:

* ``ContactEnquiry`` rarely has an upstream FK to an agency — the public
  contact form is filled before any agency relationship exists. We attempt
  a best-effort match by ``email`` against ``accounts.User.agency_id`` for
  pre-existing accounts; everything else stays null.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears ``agency_id`` (cosmetic).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.7) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    ContactEnquiry = apps.get_model("contact", "ContactEnquiry")
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)

    email_to_agency: dict[str, int] = dict(
        User.objects.filter(agency_id__isnull=False)
        .exclude(email="")
        .values_list("email", "agency_id")
    )

    qs = ContactEnquiry.objects.filter(agency__isnull=True)
    total = qs.count()
    updated = 0
    no_match = 0

    for row in qs.iterator():
        agency_id = email_to_agency.get(row.email) or email_to_agency.get((row.email or "").lower())
        if agency_id is None:
            no_match += 1
            continue
        row.agency_id = agency_id
        row.save(update_fields=["agency_id"])
        updated += 1

    print("\n[contact.0003] Backfilled agency_id on ContactEnquiry:")
    print(f"  ContactEnquiry       : {updated}/{total} updated, {no_match} orphan")
    print(f"    - no matching user by email       : {no_match}")


def reverse_clear(apps, schema_editor):
    apps.get_model("contact", "ContactEnquiry").objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("contact", "0002_add_agency_and_popia_fields_contact"),
        ("accounts", "0022_add_two_fa_method"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_clear),
    ]

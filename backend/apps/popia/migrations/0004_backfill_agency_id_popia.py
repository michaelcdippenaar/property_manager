"""
Data migration — backfill ``agency_id`` on existing ``DSARRequest`` and
``ExportJob`` rows.

Resolution chain:

* ``DSARRequest`` → ``requester.agency_id`` (the data subject who filed
  the request).
* ``ExportJob`` → parent ``DSARRequest.agency_id`` (denormalised once the
  parent is resolved).

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears ``agency_id`` (cosmetic).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.7) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    DSARRequest = apps.get_model("popia", "DSARRequest")
    ExportJob = apps.get_model("popia", "ExportJob")
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)

    user_to_agency: dict[int, int] = dict(
        User.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    # ── DSARRequest ───────────────────────────────────────────────────────────
    qs = DSARRequest.objects.filter(agency__isnull=True)
    total = qs.count()
    dsar_updated = 0
    dsar_no_requester = 0
    dsar_no_agency = 0

    for row in qs.iterator():
        if row.requester_id is None:
            dsar_no_requester += 1
            continue
        agency_id = user_to_agency.get(row.requester_id)
        if agency_id is None:
            dsar_no_agency += 1
            continue
        row.agency_id = agency_id
        row.save(update_fields=["agency_id"])
        dsar_updated += 1

    # ── ExportJob ─────────────────────────────────────────────────────────────
    dsar_to_agency: dict[int, int] = dict(
        DSARRequest.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    qs2 = ExportJob.objects.filter(agency__isnull=True)
    job_total = qs2.count()
    job_updated = 0
    job_orphan = 0

    for row in qs2.iterator():
        agency_id = dsar_to_agency.get(row.dsar_request_id)
        if agency_id is None:
            job_orphan += 1
            continue
        row.agency_id = agency_id
        row.save(update_fields=["agency_id"])
        job_updated += 1

    orphan = dsar_no_requester + dsar_no_agency
    print("\n[popia.0004] Backfilled agency_id on POPIA models:")
    print(f"  DSARRequest          : {dsar_updated}/{total} updated, {orphan} orphan")
    print(f"    - requester null                 : {dsar_no_requester}")
    print(f"    - requester without agency_id    : {dsar_no_agency}")
    print(f"  ExportJob            : {job_updated}/{job_total} updated, {job_orphan} orphan")


def reverse_clear(apps, schema_editor):
    apps.get_model("popia", "DSARRequest").objects.update(agency_id=None)
    apps.get_model("popia", "ExportJob").objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("popia", "0003_add_agency_and_popia_fields_popia"),
        ("accounts", "0022_add_two_fa_method"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_clear),
    ]

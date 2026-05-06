"""
Data migration — backfill ``agency_id`` on AI app models.

Resolution chain:

* ``TenantChatSession``  → ``user.agency_id``
* ``TenantIntelligence`` → ``user.agency_id``
* ``GuideInteraction``   → ``user.agency_id``

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears ``agency_id`` (cosmetic).

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.7) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    user_app, user_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(user_app, user_model)

    user_to_agency: dict[int, int] = dict(
        User.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )

    summary: list[str] = []

    for model_name in ("TenantChatSession", "TenantIntelligence", "GuideInteraction"):
        Model = apps.get_model("ai", model_name)
        qs = Model.objects.filter(agency__isnull=True)
        total = qs.count()
        updated = 0
        no_user = 0
        no_agency = 0

        for row in qs.iterator():
            if row.user_id is None:
                no_user += 1
                continue
            agency_id = user_to_agency.get(row.user_id)
            if agency_id is None:
                no_agency += 1
                continue
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            updated += 1

        orphan = no_user + no_agency
        summary.append(
            f"  {model_name:21s}: {updated}/{total} updated, {orphan} orphan "
            f"(no user={no_user}, no agency_id={no_agency})"
        )

    print("\n[ai.0006] Backfilled agency_id on AI models:")
    for line in summary:
        print(line)


def reverse_clear(apps, schema_editor):
    for model_name in ("TenantChatSession", "TenantIntelligence", "GuideInteraction"):
        apps.get_model("ai", model_name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0005_add_agency_and_popia_fields_ai"),
        ("accounts", "0022_add_two_fa_method"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_clear),
    ]

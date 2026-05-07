"""
Phase 4 — Backfill orphan rows in the ai app to Klikk agency #1.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 4).
"""
from __future__ import annotations

from django.db import migrations


AI_MODELS = ["TenantChatSession", "TenantIntelligence", "GuideInteraction"]


def backfill(apps, schema_editor):
    Agency = apps.get_model("accounts", "Agency")
    klikk = (
        Agency.objects.filter(pk=1).first()
        or Agency.objects.filter(name__icontains="klikk").first()
    )
    if klikk is None:
        print("[ai.0007] no Klikk agency — skipping")
        return

    counts: dict[str, int] = {}
    skipped: list[str] = []
    for label in AI_MODELS:
        try:
            Model = apps.get_model("ai", label)
        except LookupError:
            skipped.append(label)
            continue
        if not any(f.name == "agency" for f in Model._meta.fields):
            skipped.append(label)
            continue
        qs = Model.objects.filter(agency__isnull=True)
        n = qs.count()
        if n:
            qs.update(agency=klikk)
            counts[label] = n

    print(f"[ai.0007] backfilled to agency #{klikk.pk}: {counts}")
    if skipped:
        print(f"[ai.0007] skipped: {skipped}")


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0006_backfill_agency_id_ai"),
        ("accounts", "0026_backfill_orphan_users_to_agency_1"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=noop_reverse),
    ]

# Generated manually — align DB with MaintenanceSkill model (legacy title/category/summary rows).

import json

from django.db import migrations


def align_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'maintenance_maintenanceskill'
            """
        )
        cols = {r[0] for r in c.fetchall()}

        if "name" not in cols and "title" in cols:
            c.execute(
                'ALTER TABLE maintenance_maintenanceskill RENAME COLUMN title TO name'
            )
        if "trade" not in cols and "category" in cols:
            c.execute(
                'ALTER TABLE maintenance_maintenanceskill RENAME COLUMN category TO trade'
            )

        c.execute(
            """
            UPDATE maintenance_maintenanceskill SET trade = 'roofing' WHERE trade = 'roof';
            UPDATE maintenance_maintenanceskill SET trade = 'general' WHERE trade = 'garden';
            """
        )
        c.execute(
            """
            UPDATE maintenance_maintenanceskill SET difficulty = 'easy'
              WHERE difficulty IN ('tenant_diy', 'tenant diy');
            UPDATE maintenance_maintenanceskill SET difficulty = 'medium'
              WHERE difficulty = 'handy';
            UPDATE maintenance_maintenanceskill SET difficulty = 'hard'
              WHERE difficulty = 'professional';
            """
        )

        c.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'maintenance_maintenanceskill'
            """
        )
        cols = {r[0] for r in c.fetchall()}

        if "is_active" not in cols:
            c.execute(
                "ALTER TABLE maintenance_maintenanceskill "
                "ADD COLUMN is_active boolean NOT NULL DEFAULT true"
            )
        if "notes" not in cols:
            c.execute(
                "ALTER TABLE maintenance_maintenanceskill "
                "ADD COLUMN notes text NOT NULL DEFAULT ''"
            )
            if "summary" in cols:
                c.execute(
                    "UPDATE maintenance_maintenanceskill SET notes = COALESCE(summary, '')"
                )


def normalize_json_fields(apps, schema_editor):
    MaintenanceSkill = apps.get_model("maintenance", "MaintenanceSkill")
    for s in MaintenanceSkill.objects.all().only("id", "steps", "symptom_phrases"):
        changed = False
        steps = s.steps
        if steps is None:
            s.steps = []
            changed = True
        elif isinstance(steps, str):
            s.steps = [steps]
            changed = True
        elif isinstance(steps, dict):
            s.steps = [json.dumps(steps, ensure_ascii=False)]
            changed = True
        elif not isinstance(steps, list):
            s.steps = [str(steps)]
            changed = True

        sp = s.symptom_phrases
        if sp is None:
            s.symptom_phrases = []
            changed = True
        elif isinstance(sp, str):
            s.symptom_phrases = [sp]
            changed = True
        elif isinstance(sp, dict):
            s.symptom_phrases = [json.dumps(sp, ensure_ascii=False)]
            changed = True
        elif not isinstance(sp, list):
            s.symptom_phrases = [str(sp)]
            changed = True

        if changed:
            s.save(update_fields=["steps", "symptom_phrases"])


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0007_agentquestion_maintenanceactivity"),
    ]

    operations = [
        migrations.RunPython(align_columns, migrations.RunPython.noop),
        migrations.RunPython(normalize_json_fields, migrations.RunPython.noop),
    ]

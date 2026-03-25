# Repairs DBs where 0007 was marked applied but maintenance_agentquestion was never created.

from django.db import migrations


def ensure_agentquestion_table(apps, schema_editor):
    conn = schema_editor.connection
    with conn.cursor() as cursor:
        tables = conn.introspection.table_names(cursor=cursor)
    if "maintenance_agentquestion" in tables:
        return
    AgentQuestion = apps.get_model("maintenance", "AgentQuestion")
    schema_editor.create_model(AgentQuestion)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0008_align_maintenanceskill_legacy_columns"),
    ]

    operations = [
        migrations.RunPython(ensure_agentquestion_table, noop_reverse, elidable=True),
    ]

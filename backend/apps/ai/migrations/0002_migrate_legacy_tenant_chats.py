# Generated manually — copy tenant_portal.TenantAi* into ai.TenantChatSession before dropping legacy tables.

from django.db import migrations


def forwards(apps, schema_editor):
    TenantChatSession = apps.get_model("ai", "TenantChatSession")
    if TenantChatSession.objects.exists():
        return
    try:
        OldConv = apps.get_model("tenant_portal", "TenantAiConversation")
        OldMsg = apps.get_model("tenant_portal", "TenantAiMessage")
    except LookupError:
        return
    for conv in OldConv.objects.all().order_by("pk"):
        msgs = []
        for m in OldMsg.objects.filter(conversation_id=conv.pk).order_by("created_at"):
            d = {
                "id": m.pk,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "attachment_kind": m.attachment_kind or "",
            }
            att = getattr(m, "attachment", None)
            if att:
                name = getattr(att, "name", None) or ""
                if name:
                    d["attachment_storage"] = name
            msgs.append(d)
        TenantChatSession.objects.create(
            id=conv.pk,
            user_id=conv.user_id,
            title=conv.title,
            maintenance_report_suggested=conv.maintenance_report_suggested,
            messages=msgs,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence('ai_tenantchatsession','id'), "
            "COALESCE((SELECT MAX(id) FROM ai_tenantchatsession), 1));"
        )


def backwards(apps, schema_editor):
    TenantChatSession = apps.get_model("ai", "TenantChatSession")
    TenantChatSession.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("tenant_portal", "0003_tenantaiconversation_maintenance_report_suggested"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

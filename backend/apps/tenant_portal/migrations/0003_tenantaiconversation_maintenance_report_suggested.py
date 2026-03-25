from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenant_portal", "0002_tenantaimessage_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantaiconversation",
            name="maintenance_report_suggested",
            field=models.BooleanField(
                default=False,
                help_text="True once this chat has identified a maintenance issue (show structured report CTA).",
            ),
        ),
    ]

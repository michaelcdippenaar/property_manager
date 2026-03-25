from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenant_portal", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantaimessage",
            name="attachment",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="tenant_ai/%Y/%m/",
                help_text="Optional photo or video from the tenant.",
            ),
        ),
        migrations.AddField(
            model_name="tenantaimessage",
            name="attachment_kind",
            field=models.CharField(
                max_length=10,
                blank=True,
                default="",
                help_text="image, video, or empty",
            ),
        ),
    ]

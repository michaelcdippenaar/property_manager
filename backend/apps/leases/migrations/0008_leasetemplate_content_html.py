from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0007_leasetemplate_leasebuildersession"),
    ]

    operations = [
        migrations.AddField(
            model_name="leasetemplate",
            name="content_html",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Manually edited HTML content (overrides DOCX render)",
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0022_landlordchatmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="information_items",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Landlord notes ingested into the tenant maintenance RAG. "
                    "Each item: {id, label, body, category, updated_at}."
                ),
            ),
        ),
    ]

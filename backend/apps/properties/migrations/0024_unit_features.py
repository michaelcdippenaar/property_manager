from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0023_property_information_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='unit',
            name='features',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Amenity tags e.g. ['braai', 'pool', 'garage', 'pet_friendly', 'garden']",
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leases', '0016_add_barcode_to_inventory'),
    ]

    operations = [
        migrations.AddField(
            model_name='lease',
            name='previous_lease',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.deletion.SET_NULL,
                related_name='successor_lease',
                to='leases.lease',
            ),
        ),
    ]

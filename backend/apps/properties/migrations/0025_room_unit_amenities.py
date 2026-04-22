"""
Add Room model (per-unit room breakdown) and amenities JSONField on Unit.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0024_remove_name_unique_add_address_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('bedroom', 'Bedroom'),
                        ('bathroom', 'Bathroom'),
                        ('kitchen', 'Kitchen'),
                        ('living_room', 'Living Room'),
                        ('dining_room', 'Dining Room'),
                        ('study', 'Study'),
                        ('garage', 'Garage'),
                        ('storeroom', 'Storeroom'),
                        ('laundry', 'Laundry'),
                        ('balcony', 'Balcony'),
                        ('patio', 'Patio'),
                        ('other', 'Other'),
                    ],
                )),
                ('name', models.CharField(blank=True, max_length=100, help_text='e.g. Main bedroom, En-suite')),
                ('size_m2', models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True)),
                ('notes', models.TextField(blank=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('unit', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='rooms',
                    to='properties.unit',
                )),
            ],
            options={
                'ordering': ['sort_order', 'room_type'],
            },
        ),
        migrations.AddField(
            model_name='unit',
            name='amenities',
            field=models.JSONField(blank=True, default=list, help_text="List of amenity strings, e.g. ['Pool', 'Garden', 'Braai area']"),
        ),
    ]

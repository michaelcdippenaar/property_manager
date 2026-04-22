"""
Merge migration: resolves the two conflicting 0024 branches.

  Branch A: 0024_unit_features          (adds Unit.features)
  Branch B: 0025_room_unit_amenities    (adds Room model, Unit.amenities,
                                          and the 0024_remove_name_unique_add_address_unique
                                          schema fixes it depends on)

The two branches operate on different fields / models so there is no
operational conflict — this file simply declares both leaf nodes as
dependencies so Django has a single leaf going forward.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0024_unit_features'),
        ('properties', '0025_room_unit_amenities'),
    ]

    operations = [
    ]

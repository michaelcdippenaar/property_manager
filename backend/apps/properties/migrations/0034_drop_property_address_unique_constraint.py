"""
Drop the orphan unique constraint on Property.address.

Why this is needed
------------------
Migration 0024 (``remove_name_unique_add_address_unique``) declared
``address = models.TextField()`` via ``AlterField`` to remove a prior
``unique=True`` on the field. Django's autodetector compared two
``TextField()`` states and emitted a no-op SQL — so the DB-level
constraint ``properties_property_address_50a98dac_uniq`` was never
dropped despite the Python field saying otherwise.

The orphan constraint surfaced during the multi-tenant E2E walkthrough
on 2026-05-12: a fresh agency tried to create a property at the same
address as another agency's existing property and hit a 500 with
``duplicate key value violates unique constraint``. Cross-agency
collision on what should be a per-tenant descriptor.

Why no replacement
------------------
``Property.address`` is descriptive metadata, not an identifier. Two
agencies should be able to list "1 Main Street" independently. Even
within a single agency two properties may legitimately share a street
address (granny flat sub-letting; building with separately-listed
units). ``Property.id`` is the canonical identifier.

The companion ``properties_property_address_50a98dac_like`` btree index
on ``text_pattern_ops`` is left in place — it's separately useful for
``LIKE '<prefix>%'`` queries and not tied to uniqueness.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0033_add_services_facilities'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE properties_property "
                "DROP CONSTRAINT IF EXISTS properties_property_address_50a98dac_uniq;"
            ),
            # Reverse: restore the unique constraint. Note this will fail if
            # any duplicate addresses exist at the time of reverse — but
            # that's the correct behaviour (you can't restore a unique
            # constraint that the data violates).
            reverse_sql=(
                "ALTER TABLE properties_property "
                "ADD CONSTRAINT properties_property_address_50a98dac_uniq "
                "UNIQUE (address);"
            ),
        ),
    ]

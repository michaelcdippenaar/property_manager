"""
Fix UnitInfo table schema drift.

The table was originally created by the old 0003_add_unit_info migration with
columns: order, effective_from, internal_note, superseded_at.

The replacement migration 0003_unitinfo_propertyagentconfig was recorded as
applied but the table already existed so CreateModel was a no-op.
This migration adds the missing columns and reconciles the schema.
"""
from django.db import migrations


class Migration(migrations.Migration):

    atomic = False  # Run raw DDL outside Django's transaction wrapper

    dependencies = [
        ('properties', '0012_add_sars_finance_doc_types'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                -- Add property_id column (nullable first)
                ALTER TABLE properties_unitinfo
                ADD COLUMN IF NOT EXISTS property_id bigint;

                -- Populate property_id from the unit's property
                UPDATE properties_unitinfo ui
                SET property_id = u.property_id
                FROM properties_unit u
                WHERE ui.unit_id = u.id AND ui.property_id IS NULL;

                -- Make it NOT NULL now that all rows have a value
                ALTER TABLE properties_unitinfo
                ALTER COLUMN property_id SET NOT NULL;

                -- Add FK index (Django naming convention)
                CREATE INDEX IF NOT EXISTS
                    properties_unitinfo_property_id_idx
                ON properties_unitinfo (property_id);

                -- Add FK constraint
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE constraint_name = 'properties_unitinfo_property_id_fk'
                          AND table_name = 'properties_unitinfo'
                    ) THEN
                        ALTER TABLE properties_unitinfo
                        ADD CONSTRAINT properties_unitinfo_property_id_fk
                        FOREIGN KEY (property_id) REFERENCES properties_property(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;

                -- Add sort_order (seed from old 'order' column if it exists)
                ALTER TABLE properties_unitinfo
                ADD COLUMN IF NOT EXISTS sort_order smallint NOT NULL DEFAULT 0;

                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'properties_unitinfo' AND column_name = 'order'
                    ) THEN
                        UPDATE properties_unitinfo
                        SET sort_order = COALESCE("order", 0);
                    END IF;
                END $$;

                -- Add created_at / updated_at
                ALTER TABLE properties_unitinfo
                ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NOT NULL DEFAULT now();

                ALTER TABLE properties_unitinfo
                ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NOT NULL DEFAULT now();
            """,
            reverse_sql="""
                ALTER TABLE properties_unitinfo DROP COLUMN IF EXISTS property_id;
                ALTER TABLE properties_unitinfo DROP COLUMN IF EXISTS sort_order;
                ALTER TABLE properties_unitinfo DROP COLUMN IF EXISTS created_at;
                ALTER TABLE properties_unitinfo DROP COLUMN IF EXISTS updated_at;
            """,
        ),
    ]

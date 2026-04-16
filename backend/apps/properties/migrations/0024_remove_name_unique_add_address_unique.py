"""
Drop the unique constraint on Property.name.
Make PropertyDetail.erf_number unique (with null=True for blank values).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0023_property_information_items'),
    ]

    operations = [
        # Drop the old unique constraint on name
        migrations.RunSQL(
            sql='ALTER TABLE properties_property DROP CONSTRAINT IF EXISTS properties_property_name_8589012f_uniq;',
            reverse_sql='ALTER TABLE properties_property ADD CONSTRAINT properties_property_name_8589012f_uniq UNIQUE (name);',
        ),
        # Revert address back to a plain TextField (remove unique=True that was added previously)
        migrations.AlterField(
            model_name='property',
            name='address',
            field=models.TextField(),
        ),
        # Convert existing empty-string erf_number values to NULL so the unique constraint won't conflict
        migrations.RunSQL(
            sql="UPDATE properties_propertydetail SET erf_number = NULL WHERE erf_number = '';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Make erf_number unique + nullable
        migrations.AlterField(
            model_name='propertydetail',
            name='erf_number',
            field=models.CharField(max_length=30, blank=True, unique=True, null=True, help_text="e.g. ERF 3587"),
        ),
    ]

"""
Make Lease.deposit nullable so that rha_check.py's `deposit is None` guard
can fire at runtime (previously Django would reject None at the ORM layer
because the field was non-nullable).

RNT-SEC-007 — reviewer fix #6.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0019_add_pdf_render_job"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lease",
            name="deposit",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
            ),
        ),
    ]

"""
Add RHA s5(3) mandatory clause fields to the Lease model:
  - escalation_clause  (TextField, blank=True, default="")
  - renewal_clause     (TextField, blank=True, default="")
  - domicilium_address (TextField, blank=True, default="")

RNT-015 — existing lease rows receive empty-string defaults (non-breaking).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0020_lease_deposit_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="lease",
            name="escalation_clause",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "RHA s5(3)(f): describes the annual rent escalation provision "
                    "(e.g. CPI-linked or fixed %)"
                ),
            ),
        ),
        migrations.AddField(
            model_name="lease",
            name="renewal_clause",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "RHA s5(3)(f): describes renewal terms and options at lease expiry"
                ),
            ),
        ),
        migrations.AddField(
            model_name="lease",
            name="domicilium_address",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "RHA s5(3): domicilium citandi et executandi — address for formal "
                    "legal notices to the tenant"
                ),
            ),
        ),
    ]

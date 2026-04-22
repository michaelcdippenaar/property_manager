import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0018_add_rha_flags_to_lease"),
        ("tenant", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantOnboarding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "lease",
                    models.OneToOneField(
                        help_text="The lease this onboarding checklist belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onboarding",
                        to="leases.lease",
                    ),
                ),
                # v1 items
                (
                    "welcome_pack_sent",
                    models.BooleanField(
                        default=False,
                        help_text="Welcome pack / house rules document sent to tenant.",
                    ),
                ),
                ("welcome_pack_sent_at", models.DateTimeField(blank=True, null=True)),
                (
                    "deposit_received",
                    models.BooleanField(
                        default=False,
                        help_text="Deposit payment received from tenant.",
                    ),
                ),
                ("deposit_received_at", models.DateTimeField(blank=True, null=True)),
                (
                    "deposit_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Actual amount received (may differ from lease deposit).",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "first_rent_scheduled",
                    models.BooleanField(
                        default=False,
                        help_text="First rent payment scheduled / confirmed.",
                    ),
                ),
                ("first_rent_scheduled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "keys_handed_over",
                    models.BooleanField(
                        default=False,
                        help_text="Physical keys / access codes handed to tenant.",
                    ),
                ),
                ("keys_handed_over_at", models.DateTimeField(blank=True, null=True)),
                (
                    "emergency_contacts_captured",
                    models.BooleanField(
                        default=False,
                        help_text="Emergency contact details captured on the tenant record.",
                    ),
                ),
                (
                    "emergency_contacts_captured_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                # v2 deferred
                (
                    "incoming_inspection_booked",
                    models.BooleanField(
                        default=False,
                        help_text="[v2 deferred] Incoming inspection appointment booked.",
                    ),
                ),
                (
                    "incoming_inspection_booked_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "deposit_banked_trust",
                    models.BooleanField(
                        default=False,
                        help_text="[v2 deferred] Deposit transferred to trust account.",
                    ),
                ),
                ("deposit_banked_trust_at", models.DateTimeField(blank=True, null=True)),
                # metadata
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Agent notes about this onboarding.",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Set automatically when all v1 items are ticked.",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tenant Onboarding",
                "verbose_name_plural": "Tenant Onboardings",
            },
        ),
    ]

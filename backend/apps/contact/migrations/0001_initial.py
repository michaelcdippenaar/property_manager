from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContactEnquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("organisation", models.CharField(blank=True, max_length=120)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("landlord", "Private landlord"),
                            ("agency", "Rental agency"),
                            ("owner", "Body corporate / owner"),
                            ("tenant", "Tenant"),
                            ("supplier", "Supplier / contractor"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=60,
                    ),
                ),
                ("message", models.TextField(max_length=4000)),
                (
                    "consent_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp of POPIA s11(1)(a) consent acknowledgement.",
                        null=True,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=512)),
                (
                    "email_sent",
                    models.BooleanField(
                        default=False,
                        help_text="Whether the notification email to CONTACT_EMAIL was dispatched.",
                    ),
                ),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("handled", models.BooleanField(db_index=True, default=False)),
                ("notes", models.TextField(blank=True, help_text="Internal notes, not shared.")),
            ],
            options={
                "verbose_name": "contact enquiry",
                "verbose_name_plural": "contact enquiries",
                "ordering": ["-created_at"],
            },
        ),
    ]

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0021_lease_escalation_renewal_domicilium"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MoveInChecklistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "lease",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="move_in_checklist",
                        to="leases.lease",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        choices=[
                            ("keys_handover", "Keys handed over"),
                            ("utilities_notified", "Utilities notified"),
                            ("tenant_app_invite", "Tenant app invite sent"),
                            ("welcome_pack", "Welcome pack delivered"),
                        ],
                        max_length=30,
                    ),
                ),
                ("is_completed", models.BooleanField(default=False)),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="move_in_items_completed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["key"],
                "unique_together": {("lease", "key")},
            },
        ),
    ]

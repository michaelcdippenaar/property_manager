# Generated for RNT-SEC-008 — Tamper-evident audit log

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
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
                    "actor_email",
                    models.EmailField(
                        blank=True,
                        help_text="Denormalised email at time of action for resilience against user deletion",
                        max_length=254,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        help_text=(
                            "Machine-readable action code, e.g. 'lease.created', "
                            "'mandate.status_changed', 'payment.reversed', 'user.role_changed'"
                        ),
                        max_length=80,
                    ),
                ),
                (
                    "object_id",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="PK of the target object",
                        null=True,
                    ),
                ),
                (
                    "target_repr",
                    models.CharField(
                        blank=True,
                        help_text="str() of the target object at the time of the event",
                        max_length=255,
                    ),
                ),
                (
                    "before_snapshot",
                    models.JSONField(
                        blank=True,
                        help_text="Model field dict before this change (null for creation events)",
                        null=True,
                    ),
                ),
                (
                    "after_snapshot",
                    models.JSONField(
                        blank=True,
                        help_text="Model field dict after this change (null for deletion events)",
                        null=True,
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        help_text="Client IP at time of action (null for signal-only/system events)",
                        null=True,
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(
                        blank=True,
                        help_text="HTTP User-Agent at time of action",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                        help_text="UTC timestamp of the event",
                    ),
                ),
                (
                    "prev_hash",
                    models.CharField(
                        blank=True,
                        help_text="self_hash of the immediately preceding AuditEvent ('' for genesis)",
                        max_length=64,
                    ),
                ),
                (
                    "self_hash",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="SHA-256 of (prev_hash || canonical_json(payload))",
                        max_length=64,
                    ),
                ),
                (
                    "retention_years",
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text="Minimum years to retain this event (FICA=5, RHA=3; default 5)",
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who triggered the action (null = system/signal-driven)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events_authored",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        blank=True,
                        help_text="Django ContentType of the target object",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit Event",
                "verbose_name_plural": "Audit Events",
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["content_type", "object_id", "timestamp"],
                name="audit_audte_content_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["action", "timestamp"],
                name="audit_audte_action_idx",
            ),
        ),
    ]

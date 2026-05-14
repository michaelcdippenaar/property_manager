"""Add POPIA accountability fields to AILeaseAgentRun.

P0-7: template FK, created_by FK, agency FK, user_message, document_html_before,
      document_html_after.
P0-10: drop unique=True from request_id (prevent IntegrityError on retry).

Migration is safe to run against staging DB rows — all new fields are nullable
or have empty-string defaults. Wraps in a transaction (implicit for DDL in
PostgreSQL). Rollback: remove the column additions and re-add unique constraint.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0031_ailease_agent_run"),
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # P0-10: drop unique constraint on request_id.
        # We rely on (request_id, started_at) for idempotency — the view
        # generates a fresh server-side uuid4 per request; the run_id from
        # audit_persisted SSE event is the pk.
        migrations.AlterField(
            model_name="aileaseagentrun",
            name="request_id",
            field=models.CharField(db_index=True, max_length=64),
        ),
        # P0-7: POPIA s14/s24 accountability fields
        migrations.AddField(
            model_name="aileaseagentrun",
            name="template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_runs",
                to="leases.leasetemplate",
                help_text="Template being edited — POPIA s14 accountability.",
            ),
        ),
        migrations.AddField(
            model_name="aileaseagentrun",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_lease_runs",
                to=settings.AUTH_USER_MODEL,
                help_text="User who triggered the run — POPIA s24 accountability.",
            ),
        ),
        migrations.AddField(
            model_name="aileaseagentrun",
            name="agency",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ai_lease_runs",
                to="accounts.agency",
                help_text="Owning agency — POPIA s14 accountability.",
            ),
        ),
        migrations.AddField(
            model_name="aileaseagentrun",
            name="user_message",
            field=models.TextField(
                blank=True,
                default="",
                help_text="The user's verbatim request — POPIA accountability trail.",
            ),
        ),
        migrations.AddField(
            model_name="aileaseagentrun",
            name="document_html_before",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Template HTML before the AI mutation — diff baseline.",
            ),
        ),
        migrations.AddField(
            model_name="aileaseagentrun",
            name="document_html_after",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Template HTML after the AI mutation — audit trail.",
            ),
        ),
    ]

"""Add ``AILeaseAgentRun`` model — per-request telemetry for the Lease AI
multi-agent loop.

Persisted by ``apps.leases.agent_runner.LeaseAgentRunner.finalize()`` at the
end of each ``/ai-chat-v2/`` request. Owns budget telemetry (LLM call count,
wall-clock, retry count, running cost) and the call log for debugging.

See ``docs/system/lease-ai-agent-architecture.md`` §7.3 + decision 20.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0030_backfill_legacy_services_to_new_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="AILeaseAgentRun",
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
                    "request_id",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("lease_id", models.BigIntegerField(blank=True, null=True)),
                ("intent", models.CharField(max_length=32)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("llm_call_count", models.PositiveSmallIntegerField(default=0)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                ("wall_clock_seconds", models.FloatField(default=0)),
                (
                    "running_cost_usd",
                    models.DecimalField(decimal_places=4, default=0, max_digits=6),
                ),
                (
                    "terminated_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("completed", "Completed"),
                            ("cap_calls", "Hit LLM-call cap"),
                            ("cap_walltime", "Hit wall-clock cap"),
                            ("cap_cost", "Hit cost cap"),
                            ("cap_retries", "Hit retry cap"),
                            ("error", "Unhandled error"),
                        ],
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "corpus_version",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                ("call_log", models.JSONField(default=list)),
                ("result_summary", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(
                        fields=["intent", "-started_at"],
                        name="lease_airun_intent_idx",
                    ),
                    models.Index(
                        fields=["terminated_reason"], name="lease_airun_term_idx"
                    ),
                ],
            },
        ),
    ]

"""
Weekly KB coverage health-check for the tenant AI chat.

Scans recent TenantChatSession interactions to count:
  - Total messages sent by tenants
  - Messages where needs_staff_input was flagged (knowledge gap / fallback)
  - Messages that created maintenance requests (successfully triaged)

Emits a summary to stdout (suitable for cron output / email alert).
Exits with code 1 if the miss-rate exceeds COVERAGE_ALERT_THRESHOLD (default 20%).

Usage:
    python manage.py tenant_chat_coverage_check
    python manage.py tenant_chat_coverage_check --days 14
    python manage.py tenant_chat_coverage_check --days 30 --alert-threshold 0.15

Scheduling:
    Cron: 0 8 * * 1 python manage.py tenant_chat_coverage_check  (every Monday at 08:00)
    Celery beat: schedule("tenant_chat_coverage_check", "weekly")
"""
from __future__ import annotations

import sys
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

COVERAGE_ALERT_THRESHOLD_DEFAULT = 0.20  # 20% miss-rate triggers alert


class Command(BaseCommand):
    help = "Weekly KB coverage check for tenant AI chat — emits coverage metrics and alerts on regressions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to look back (default: 7)",
        )
        parser.add_argument(
            "--alert-threshold",
            type=float,
            default=COVERAGE_ALERT_THRESHOLD_DEFAULT,
            dest="alert_threshold",
            help=(
                f"Miss-rate threshold above which exit code 1 is returned "
                f"(default: {COVERAGE_ALERT_THRESHOLD_DEFAULT:.0%})"
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print metrics as JSON (suitable for log ingestion)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        alert_threshold = options["alert_threshold"]
        as_json = options["json"]

        since = timezone.now() - timedelta(days=days)
        metrics = self._compute_metrics(since)

        if as_json:
            import json
            self.stdout.write(json.dumps(metrics, default=str))
            if metrics["miss_rate"] > alert_threshold:
                sys.exit(1)
            return

        self._print_report(metrics, days, alert_threshold)

        if metrics["miss_rate"] > alert_threshold:
            self.stderr.write(
                self.style.ERROR(
                    f"\nALERT: miss-rate {metrics['miss_rate']:.1%} exceeds threshold "
                    f"{alert_threshold:.1%}. Review coverage and add missing KB articles."
                )
            )
            sys.exit(1)

    def _compute_metrics(self, since) -> dict:
        """
        Analyse TenantChatSession.messages for the period.

        We look for:
        - agent_question_id set (AI flagged needs_staff_input)
        - maintenance_request_id set (AI successfully triaged a repair)
        """
        from apps.ai.models import TenantChatSession

        sessions = TenantChatSession.objects.filter(updated_at__gte=since)

        total_sessions = sessions.count()
        sessions_with_fallback = sessions.filter(agent_question__isnull=False).count()
        sessions_with_mr = sessions.filter(maintenance_request__isnull=False).count()

        # Count total user messages across all sessions
        total_user_messages = 0
        sessions_with_messages = sessions.only("messages")
        for session in sessions_with_messages:
            for msg in (session.messages or []):
                if msg.get("role") == "user":
                    total_user_messages += 1

        # Miss-rate: sessions where AI couldn't answer (needed staff input)
        # relative to all sessions that had at least one message
        sessions_with_any_message = sessions.exclude(messages=[]).count()
        miss_rate = (
            sessions_with_fallback / sessions_with_any_message
            if sessions_with_any_message > 0
            else 0.0
        )

        # Coverage rate: sessions fully handled (either answered or MR created, no fallback)
        sessions_handled = sessions_with_any_message - sessions_with_fallback
        coverage_rate = (
            sessions_handled / sessions_with_any_message
            if sessions_with_any_message > 0
            else 1.0
        )

        return {
            "period_days": int((sessions.first().updated_at - sessions.last().updated_at).days) if sessions.count() >= 2 else 0,
            "since": since.isoformat(),
            "total_sessions": total_sessions,
            "sessions_with_messages": sessions_with_any_message,
            "total_user_messages": total_user_messages,
            "sessions_with_fallback": sessions_with_fallback,
            "sessions_with_maintenance_request": sessions_with_mr,
            "sessions_handled_by_ai": sessions_handled,
            "miss_rate": round(miss_rate, 4),
            "coverage_rate": round(coverage_rate, 4),
        }

    def _print_report(self, m: dict, days: int, threshold: float) -> None:
        self.stdout.write(self.style.NOTICE(
            f"\n=== Tenant Chat KB Coverage Report (last {days} days) ===\n"
        ))
        self.stdout.write(f"Since:                        {m['since']}")
        self.stdout.write(f"Total sessions:               {m['total_sessions']}")
        self.stdout.write(f"Sessions with messages:        {m['sessions_with_messages']}")
        self.stdout.write(f"Total tenant messages:         {m['total_user_messages']}")
        self.stdout.write("")
        self.stdout.write(f"Handled by AI:                {m['sessions_handled_by_ai']}")
        self.stdout.write(f"Maintenance requests created: {m['sessions_with_maintenance_request']}")
        self.stdout.write(f"Escalated to agent:           {m['sessions_with_fallback']}")
        self.stdout.write("")

        coverage_pct = f"{m['coverage_rate']:.1%}"
        miss_pct = f"{m['miss_rate']:.1%}"

        if m["miss_rate"] <= threshold:
            self.stdout.write(self.style.SUCCESS(
                f"Coverage rate: {coverage_pct}  |  Miss rate: {miss_pct}  [OK]"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Coverage rate: {coverage_pct}  |  Miss rate: {miss_pct}  [ABOVE THRESHOLD {threshold:.1%}]"
            ))

        self.stdout.write(
            f"\nNote: 'Escalated to agent' counts sessions where the AI flagged "
            f"needs_staff_input=true and said 'Let me hand you to your agent'."
        )
        self.stdout.write(
            "To improve coverage, add KB articles under backend/apps/chat/knowledge/ "
            "and re-run: python manage.py ingest_chat_kb"
        )

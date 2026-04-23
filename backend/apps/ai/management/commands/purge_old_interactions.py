"""
Management command: purge_old_interactions

Enforces the POPIA s72 / GDPR-equivalent retention policy for AI chat logs:

  - GuideInteraction rows older than GUIDE_INTERACTION_RETENTION_DAYS
    (default 90) are hard-deleted.
  - TenantChatSession rows whose `updated_at` is older than
    TENANT_CHAT_SESSION_RETENTION_DAYS (default 90) are hard-deleted.

Designed to be run as a scheduled task (e.g. daily cron or Celery beat).

Usage:
    python manage.py purge_old_interactions
    python manage.py purge_old_interactions --dry-run
    python manage.py purge_old_interactions --days 60
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

# Retention threshold in days.  Can be overridden in Django settings.
_DEFAULT_RETENTION_DAYS = 90


class Command(BaseCommand):
    help = (
        "Delete GuideInteraction and TenantChatSession records older than the "
        "configured retention window (default 90 days).  "
        "POPIA s72 compliance obligation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Override retention threshold in days "
                f"(default: {_DEFAULT_RETENTION_DAYS} or settings value)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print counts without deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        days: int = options["days"] or int(
            getattr(settings, "AI_INTERACTION_RETENTION_DAYS", _DEFAULT_RETENTION_DAYS)
        )
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.NOTICE(
                f"[purge_old_interactions] retention={days} days  "
                f"cutoff={cutoff.date().isoformat()}  "
                f"dry_run={dry_run}"
            )
        )

        # ── GuideInteraction ──────────────────────────────────────────────
        from apps.ai.models import GuideInteraction

        gi_qs = GuideInteraction.objects.filter(created_at__lt=cutoff)
        gi_count = gi_qs.count()
        if dry_run:
            self.stdout.write(f"  GuideInteraction: {gi_count} rows would be deleted.")
        else:
            deleted, _ = gi_qs.delete()
            self.stdout.write(
                self.style.SUCCESS(f"  GuideInteraction: {deleted} rows deleted.")
            )
            logger.info("purge_old_interactions: deleted %d GuideInteraction rows (cutoff=%s)", deleted, cutoff)

        # ── TenantChatSession ─────────────────────────────────────────────
        from apps.ai.models import TenantChatSession

        tcs_qs = TenantChatSession.objects.filter(updated_at__lt=cutoff)
        tcs_count = tcs_qs.count()
        if dry_run:
            self.stdout.write(f"  TenantChatSession: {tcs_count} rows would be deleted.")
        else:
            deleted, _ = tcs_qs.delete()
            self.stdout.write(
                self.style.SUCCESS(f"  TenantChatSession: {deleted} rows deleted.")
            )
            logger.info("purge_old_interactions: deleted %d TenantChatSession rows (cutoff=%s)", deleted, cutoff)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run complete — no data was deleted.")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Purge complete."))

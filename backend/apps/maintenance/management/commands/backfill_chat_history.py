"""
One-off command to backfill MaintenanceActivity records from TenantChatSession
messages that were never persisted (bug fix for chat history persistence).

Usage:
    python manage.py backfill_chat_history          # dry-run (default)
    python manage.py backfill_chat_history --apply   # actually create records
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ai.models import TenantChatSession
from apps.maintenance.chat_history import persist_chat_history_to_request


class Command(BaseCommand):
    help = "Backfill MaintenanceActivity from TenantChatSession messages that were never persisted."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Actually create the activity records (default is dry-run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        sessions = (
            TenantChatSession.objects
            .filter(maintenance_request__isnull=False)
            .select_related("maintenance_request", "user")
        )

        total_created = 0
        for session in sessions:
            mr = session.maintenance_request
            messages = session.messages or []
            if not messages:
                continue

            if apply:
                created = persist_chat_history_to_request(
                    mr,
                    messages,
                    created_by=session.user,
                    session_id=session.pk,
                    source="tenant_chat",
                )
            else:
                # Dry-run: count messages that would be created
                from apps.maintenance.models import MaintenanceActivity
                existing_ids = set(
                    MaintenanceActivity.objects.filter(
                        request=mr,
                        metadata__chat_source="tenant_chat",
                    )
                    .exclude(metadata__chat_message_id=None)
                    .values_list("metadata__chat_message_id", flat=True)
                )
                created = sum(
                    1 for msg in messages
                    if (msg.get("content") or "").strip()
                    and (msg.get("type") or "") not in {"skills", "confirm"}
                    and msg.get("id") not in existing_ids
                )

            if created:
                self.stdout.write(
                    f"  Session #{session.pk} → MR #{mr.pk}: "
                    f"{'created' if apply else 'would create'} {created} activities"
                )
                total_created += created

        mode = "Created" if apply else "Would create (dry-run)"
        self.stdout.write(self.style.SUCCESS(
            f"\n{mode} {total_created} activity records across {sessions.count()} sessions."
        ))
        if not apply:
            self.stdout.write("Run with --apply to execute.")

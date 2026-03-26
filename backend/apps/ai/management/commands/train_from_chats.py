"""
Self-training pipeline: extract knowledge from resolved chat sessions.

Scans TenantChatSessions that have linked MaintenanceRequests (resolved or
closed), summarises the tenant↔AI interaction, and ingests the summary into
the chat_knowledge RAG collection.

This allows the AI to learn from its own successful interactions:
  - What symptoms map to which categories
  - What resolution advice worked
  - Common tenant concerns per property

Usage:
    python manage.py train_from_chats
    python manage.py train_from_chats --limit 100
    python manage.py train_from_chats --reset  # Clear and rebuild
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.ai.models import TenantChatSession
from apps.maintenance.models import MaintenanceRequest
from core.contract_rag import get_chat_knowledge_collection, ingest_chat_knowledge


class Command(BaseCommand):
    help = "Extract knowledge from resolved chat sessions for AI self-training"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max sessions to process (0 = all)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear the chat_knowledge collection before re-ingesting",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be ingested without actually doing it",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        reset = options["reset"]
        dry_run = options["dry_run"]

        if reset and not dry_run:
            self.stdout.write("Clearing chat_knowledge collection...")
            try:
                from core.contract_rag import get_chroma_client, CHAT_KNOWLEDGE_COLLECTION
                client = get_chroma_client()
                client.delete_collection(CHAT_KNOWLEDGE_COLLECTION)
                self.stdout.write(self.style.SUCCESS("Collection cleared."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not clear: {e}"))

        # Find sessions with resolved/closed maintenance requests
        resolved_statuses = [
            MaintenanceRequest.Status.RESOLVED,
            MaintenanceRequest.Status.CLOSED,
        ]
        sessions = (
            TenantChatSession.objects
            .filter(
                maintenance_request__isnull=False,
                maintenance_request__status__in=resolved_statuses,
            )
            .select_related("maintenance_request", "user")
            .order_by("-updated_at")
        )

        if limit > 0:
            sessions = sessions[:limit]

        processed = 0
        ingested = 0
        skipped = 0

        for session in sessions:
            processed += 1
            mr = session.maintenance_request
            messages = session.messages or []

            if len(messages) < 2:
                skipped += 1
                continue

            # Build a knowledge summary from the interaction
            summary = self._build_summary(session, mr, messages)
            if not summary:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"\n--- Session #{session.pk} ---")
                self.stdout.write(summary[:500])
                self.stdout.write("---")
                ingested += 1
                continue

            # Determine property_id from the maintenance request
            prop_id = None
            try:
                if mr.unit and mr.unit.property_id:
                    prop_id = mr.unit.property_id
            except Exception:
                pass

            success = ingest_chat_knowledge(
                session_id=session.pk,
                summary=summary,
                category=mr.category or "other",
                property_id=prop_id,
            )
            if success:
                ingested += 1
            else:
                skipped += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Processed: {processed}, Ingested: {ingested}, Skipped: {skipped}"
            )
        )

        if not dry_run:
            try:
                col = get_chat_knowledge_collection()
                self.stdout.write(
                    f"Chat knowledge collection now has {col.count()} entries."
                )
            except Exception:
                pass

    def _build_summary(
        self,
        session: TenantChatSession,
        mr: MaintenanceRequest,
        messages: list,
    ) -> str:
        """
        Build a concise knowledge summary from a resolved chat session.

        Format:
          Issue: {title}
          Category: {category} | Priority: {priority} | Status: {status}
          Symptoms reported: {tenant's first message}
          Resolution: {last assistant message}
          Key exchange: {condensed conversation}
        """
        # Extract tenant's initial report
        first_user_msg = ""
        for m in messages:
            if m.get("role") == "user":
                first_user_msg = (m.get("content") or "").strip()[:500]
                break

        # Extract last assistant message (likely contains resolution advice)
        last_assistant_msg = ""
        for m in reversed(messages):
            if m.get("role") == "assistant":
                last_assistant_msg = (m.get("content") or "").strip()[:500]
                break

        if not first_user_msg:
            return ""

        # Condensed conversation (alternating, truncated)
        exchange_parts = []
        for m in messages[:10]:  # First 10 messages
            role = "Tenant" if m.get("role") == "user" else "Agent"
            text = (m.get("content") or "").strip()[:200]
            if text:
                exchange_parts.append(f"{role}: {text}")
        exchange = "\n".join(exchange_parts)

        return (
            f"Issue: {mr.title}\n"
            f"Category: {mr.category} | Priority: {mr.priority} | Status: {mr.status}\n"
            f"Symptoms reported: {first_user_msg}\n"
            f"Resolution advice: {last_assistant_msg}\n"
            f"Conversation:\n{exchange}"
        )

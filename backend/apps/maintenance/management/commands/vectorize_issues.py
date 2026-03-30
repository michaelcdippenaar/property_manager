"""
Vectorize maintenance issues into ChromaDB for RAG similarity search.

This creates a clear path for the AI to find relevant past issues:
  New issue → vector search → similar past issues with resolutions

Usage:
    python manage.py vectorize_issues          # ingest all issues
    python manage.py vectorize_issues --reset  # clear and re-ingest
    python manage.py vectorize_issues --status resolved  # only resolved
    python manage.py vectorize_issues --limit 100
"""
from django.core.management.base import BaseCommand

from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest
from core.contract_rag import ingest_maintenance_issue


class Command(BaseCommand):
    help = "Vectorize maintenance issues into ChromaDB for RAG similarity search"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Clear collection before ingesting")
        parser.add_argument("--status", type=str, help="Only ingest issues with this status")
        parser.add_argument("--limit", type=int, default=0, help="Max issues to ingest")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested")

    def handle(self, *args, **options):
        if options["reset"]:
            from core.contract_rag import get_chroma_client, MAINTENANCE_ISSUES_COLLECTION
            try:
                client = get_chroma_client()
                client.delete_collection(MAINTENANCE_ISSUES_COLLECTION)
                self.stdout.write("Cleared maintenance_issues collection")
            except Exception:
                pass

        qs = MaintenanceRequest.objects.select_related(
            "unit__property", "tenant"
        ).order_by("-created_at")

        if options["status"]:
            qs = qs.filter(status=options["status"])

        if options["limit"]:
            qs = qs[:options["limit"]]

        ingested = 0
        errors = 0

        for req in qs:
            # Build resolution text from activity log
            resolution_activities = MaintenanceActivity.objects.filter(
                request=req
            ).order_by("created_at")

            resolution_parts = []
            for a in resolution_activities:
                author = a.created_by.full_name if a.created_by else "AI Agent"
                resolution_parts.append(f"[{author}]: {a.message}")
            resolution = "\n".join(resolution_parts[-5:]) if resolution_parts else ""

            if options["dry_run"]:
                self.stdout.write(
                    f"  Would ingest #{req.pk}: {req.title} "
                    f"[{req.category}/{req.priority}] ({len(resolution)} chars resolution)"
                )
                ingested += 1
                continue

            property_id = req.unit.property_id if req.unit else None
            success = ingest_maintenance_issue(
                request_id=req.pk,
                title=req.title,
                description=req.description,
                category=req.category,
                priority=req.priority,
                status=req.status,
                property_id=property_id,
                resolution=resolution,
            )
            if success:
                ingested += 1
            else:
                errors += 1

        action = "Would ingest" if options["dry_run"] else "Ingested"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {ingested} maintenance issues, {errors} errors"
            )
        )

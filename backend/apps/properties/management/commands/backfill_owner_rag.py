"""
Backfill the owner_documents RAG collection for every Landlord with
existing classification_data. Safe to re-run — each landlord's chunks are
dropped and re-ingested.

    python manage.py backfill_owner_rag
    python manage.py backfill_owner_rag --landlord 42
    python manage.py backfill_owner_rag --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.properties.models import Landlord
from apps.properties.tasks import ingest_owner_documents


class Command(BaseCommand):
    help = "Re-ingest every classified landlord's documents into the owner_documents ChromaDB collection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--landlord", type=int, default=None,
            help="Only backfill this landlord_id (useful for debugging).",
        )
        parser.add_argument(
            "--include-unclassified", action="store_true",
            help="Include landlords whose classification_data is empty. Off by default because gap analysis needs it.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="List which landlords would be processed without ingesting.",
        )

    def handle(self, *args, **options):
        qs = Landlord.objects.all().order_by("pk")
        if options["landlord"]:
            qs = qs.filter(pk=options["landlord"])
        if not options["include_unclassified"]:
            qs = qs.exclude(classification_data__isnull=True)

        landlords = list(qs)
        self.stdout.write(f"Found {len(landlords)} landlord(s) to process.")

        if options["dry_run"]:
            for l in landlords:
                self.stdout.write(f"  - #{l.pk} {l.name} ({l.landlord_type})")
            return

        total_chunks = 0
        for l in landlords:
            try:
                n = ingest_owner_documents(l.pk)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  #{l.pk} {l.name}: FAILED — {exc}"))
                continue
            total_chunks += n
            self.stdout.write(f"  #{l.pk} {l.name}: {n} chunks")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(landlords)} landlords processed, {total_chunks} total chunks ingested."
        ))

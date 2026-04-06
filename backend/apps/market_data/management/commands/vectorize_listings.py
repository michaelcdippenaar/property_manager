"""
Vectorize market listings into ChromaDB for semantic search.

Idempotent — uses listing PKs as document IDs so re-runs update existing vectors.

Usage:
  python manage.py vectorize_listings
  python manage.py vectorize_listings --area stellenbosch
  python manage.py vectorize_listings --area stellenbosch --reset
  python manage.py vectorize_listings --limit 200 --batch-size 32
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from apps.market_data.models import MarketListing, WINELANDS_AREAS
from apps.market_data.management.commands.enrich_market_listings import (
    _build_embedding_text,
    _upsert_to_chromadb,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Upsert Winelands market listings into ChromaDB (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument("--area", help="Filter by area slug (default: all winelands)")
        parser.add_argument("--reset", action="store_true", help="Delete existing vectors for the area before upserting")
        parser.add_argument("--limit", type=int, help="Max listings to vectorize per run")
        parser.add_argument("--batch-size", type=int, default=64)

    def handle(self, *args, **options):
        area = options.get("area")
        do_reset = options["reset"]
        limit = options.get("limit")
        batch_size = options["batch_size"]

        # Reset vectors for the area if requested
        if do_reset:
            try:
                from core.contract_rag import get_market_listings_collection
                collection = get_market_listings_collection()
                where = {"area": area} if area else {"area": {"$in": [a.value for a in WINELANDS_AREAS]}}
                existing = collection.get(where=where)
                if existing["ids"]:
                    collection.delete(ids=existing["ids"])
                    self.stdout.write(self.style.WARNING(
                        f"Deleted {len(existing['ids'])} existing vectors"
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Reset failed: {e}"))

        # Build queryset
        qs = MarketListing.objects.all()
        if area:
            qs = qs.filter(area=area)
        else:
            qs = qs.filter(area__in=[a.value for a in WINELANDS_AREAS])
        qs = qs.order_by("-first_seen_at")
        if limit:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Vectorizing {total} listings (batch_size={batch_size})...")

        upserted = failed = 0

        # Process in batches
        batch: list[MarketListing] = []
        for listing in qs.iterator():
            batch.append(listing)
            if len(batch) >= batch_size:
                u, f = self._flush_batch(batch)
                upserted += u
                failed += f
                batch = []
                self.stdout.write(f"  {upserted}/{total} vectorized...", ending="\r")

        if batch:
            u, f = self._flush_batch(batch)
            upserted += u
            failed += f

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. vectorized={upserted} failed={failed} total={total}"
        ))

    def _flush_batch(self, listings: list[MarketListing]) -> tuple[int, int]:
        upserted = failed = 0
        for listing in listings:
            try:
                text = _build_embedding_text(listing)
                _upsert_to_chromadb(listing, text)
                upserted += 1
            except Exception as e:
                logger.warning("Failed to vectorize listing %s: %s", listing.pk, e)
                failed += 1
        return upserted, failed

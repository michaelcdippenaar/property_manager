"""
Classify market listings using Claude Vision (street view images).

Writes ai_property_type, ai_condition, ai_style, ai_classification_confidence,
and ai_classified_at back to the MarketListing record.

Default limit is 50 per run to control Claude API costs.

Usage:
  python manage.py classify_properties
  python manage.py classify_properties --area stellenbosch --limit 50
  python manage.py classify_properties --listing-id 42
  python manage.py classify_properties --force --limit 20   # re-classify already done
  python manage.py classify_properties --dry-run --limit 10
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.market_data.models import MarketListing, WINELANDS_AREAS
from apps.market_data.services.property_classifier import PropertyClassifier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Classify market listings using Claude Vision (property type, condition, style)"

    def add_arguments(self, parser):
        parser.add_argument("--listing-id", type=int, help="Classify a single listing by ID")
        parser.add_argument("--area", help="Filter by area slug (default: all winelands)")
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Max listings to classify per run (default 50 — API cost control)",
        )
        parser.add_argument("--force", action="store_true", help="Re-classify already-classified listings")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be classified without calling API")

    def handle(self, *args, **options):
        listing_id = options.get("listing_id")
        area = options.get("area")
        limit = options["limit"]
        force = options["force"]
        dry_run = options["dry_run"]

        classifier = PropertyClassifier()
        if not classifier.available and not dry_run:
            self.stdout.write(self.style.ERROR(
                "ANTHROPIC_API_KEY not set — cannot classify. Use --dry-run to preview."
            ))
            return

        # Build queryset: require saved street view with OK status
        qs = MarketListing.objects.filter(
            street_view__api_status="OK",
            street_view__photo_file__isnull=False,
        ).select_related("street_view")

        if listing_id:
            qs = qs.filter(pk=listing_id)
        else:
            if area:
                qs = qs.filter(area=area)
            else:
                qs = qs.filter(area__in=[a.value for a in WINELANDS_AREAS])
            if not force:
                qs = qs.filter(ai_classified_at__isnull=True)
            qs = qs.order_by("-first_seen_at")[:limit]

        total = qs.count()
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN — would classify {total} listings"))
            for listing in qs[:10]:
                self.stdout.write(
                    f"  [{listing.pk}] {listing.suburb or listing.area} "
                    f"({listing.source}) — {listing.get_property_type_display() or 'unknown type'}"
                )
            return

        self.stdout.write(f"Classifying {total} listings with Claude Vision...")
        classified = skipped = failed = 0

        for listing in qs.iterator():
            self.stdout.write(
                f"  [{listing.pk}] {listing.suburb or listing.area} ({listing.source}) ...",
                ending="",
            )
            result = classifier.classify_from_street_view(listing)

            if result is None:
                skipped += 1
                self.stdout.write(" — no result")
                continue

            try:
                listing.ai_property_type             = result.get("property_type", "")[:30]
                listing.ai_condition                 = result.get("condition", "")[:20]
                listing.ai_style                     = result.get("style", "")[:30]
                listing.ai_classification_confidence = result.get("confidence")
                listing.ai_classified_at             = timezone.now()
                listing.save(update_fields=[
                    "ai_property_type",
                    "ai_condition",
                    "ai_style",
                    "ai_classification_confidence",
                    "ai_classified_at",
                ])
                classified += 1
                confidence = result.get("confidence", 0)
                self.stdout.write(
                    f" {result['property_type']} / {result['condition']} / {result['style']} "
                    f"(conf={confidence:.2f})"
                )
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f" ✗ {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. classified={classified} skipped={skipped} failed={failed}"
        ))

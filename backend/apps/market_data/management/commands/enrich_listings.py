"""
Enrich Winelands market listings with Google Maps data and ChromaDB vectorization.

Wrapper around enrich_market_listings with Winelands defaults and a --re-enrich flag.

Usage:
  python manage.py enrich_listings
  python manage.py enrich_listings --area stellenbosch --limit 50
  python manage.py enrich_listings --area stellenbosch --re-enrich
  python manage.py enrich_listings --skip-streetview --skip-places --limit 200
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.market_data.models import MarketListing, WINELANDS_AREAS


class Command(BaseCommand):
    help = "Enrich Winelands listings with Street View, nearby places, and vector embeddings"

    def add_arguments(self, parser):
        parser.add_argument("--area", help="Filter by area slug (default: all winelands)")
        parser.add_argument("--limit", type=int, default=100, help="Max listings to enrich per run")
        parser.add_argument("--skip-streetview", action="store_true")
        parser.add_argument("--skip-places", action="store_true")
        parser.add_argument("--skip-vectorize", action="store_true")
        parser.add_argument(
            "--re-enrich",
            action="store_true",
            help="Clear enriched_at flag first, forcing re-enrichment of already-enriched listings",
        )

    def handle(self, *args, **options):
        area = options.get("area")
        re_enrich = options["re_enrich"]

        if re_enrich:
            qs = MarketListing.objects.filter(enriched_at__isnull=False)
            if area:
                qs = qs.filter(area=area)
            else:
                qs = qs.filter(area__in=[a.value for a in WINELANDS_AREAS])
            count = qs.update(enriched_at=None)
            self.stdout.write(self.style.WARNING(f"Cleared enriched_at for {count} listings (re-enrich mode)"))

        kwargs = {
            "limit": options["limit"],
            "skip_streetview": options["skip_streetview"],
            "skip_places": options["skip_places"],
            "skip_vectorize": options["skip_vectorize"],
        }
        if area:
            kwargs["area"] = area

        call_command("enrich_market_listings", **kwargs)

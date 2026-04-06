"""
Scrape all 8 property portals for Winelands areas (Stellenbosch, Paarl,
Franschhoek, Somerset West, Strand).

Usage:
  python manage.py scrape_winelands
  python manage.py scrape_winelands --area stellenbosch
  python manage.py scrape_winelands --area stellenbosch --source property24 --listing-type rent
  python manage.py scrape_winelands --dry-run
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command

from apps.market_data.models import WINELANDS_AREAS


class Command(BaseCommand):
    help = "Scrape all 8 property portals for Winelands areas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--area",
            default="winelands",
            help="winelands (all 5) or a single area slug: stellenbosch|paarl|franschhoek|somerset_west|strand",
        )
        parser.add_argument(
            "--source",
            default="all",
            help="Source slug or 'all'",
        )
        parser.add_argument(
            "--listing-type",
            default="both",
            help="rent|sale|both",
        )
        parser.add_argument("--news", action="store_true", help="Also scrape area news feeds")
        parser.add_argument("--bylaws", action="store_true", help="Also scrape municipal bylaws")
        parser.add_argument("--dry-run", action="store_true", help="Parse without saving to DB")

    def handle(self, *args, **options):
        area_opt = options["area"]

        if area_opt == "winelands":
            area_str = ",".join(a.value for a in WINELANDS_AREAS)
            self.stdout.write(
                self.style.SUCCESS(f"Scraping all Winelands areas: {area_str}")
            )
        else:
            area_str = area_opt
            self.stdout.write(self.style.SUCCESS(f"Scraping area: {area_str}"))

        call_command(
            "scrape_market_data",
            source=options["source"],
            area=area_str,
            listing_type=options["listing_type"],
            news=options["news"],
            bylaws=options["bylaws"],
            dry_run=options["dry_run"],
        )

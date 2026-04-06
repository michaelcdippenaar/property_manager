"""
Management command to scrape property market data from all configured sources.

Usage:
  python manage.py scrape_market_data
  python manage.py scrape_market_data --source property24 --area stellenbosch --listing-type rent
  python manage.py scrape_market_data --news --bylaws
  python manage.py scrape_market_data --source property24 --dry-run
"""
from __future__ import annotations

import traceback
from datetime import date, datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.market_data.models import (
    AreaSlug,
    AreaNewsArticle,
    ListingAgency,
    ListingType,
    MarketListing,
    MarketListingPhoto,
    MarketPriceStats,
    MunicipalBylaw,
    ScrapeRun,
    SourceSlug,
)

ALL_SOURCES = [
    SourceSlug.PROPERTY24,
    SourceSlug.PRIVATE_PROPERTY,
    SourceSlug.GUMTREE,
    SourceSlug.IOL_PROPERTY,
    SourceSlug.RENTFIND,
    SourceSlug.PAM_GOLDING,
    SourceSlug.SEEFF,
    SourceSlug.ANNA_BASSON,
    SourceSlug.ENGEL_VOLKERS,
    SourceSlug.SOTHEBYS,
    SourceSlug.CHAS_EVERITT,
    SourceSlug.LOUW_COETZEE,
]

SCRAPER_MAP = {
    SourceSlug.PROPERTY24:       "apps.market_data.scrapers.property24.Property24Scraper",
    SourceSlug.PRIVATE_PROPERTY: "apps.market_data.scrapers.private_property.PrivatePropertyScraper",
    SourceSlug.GUMTREE:          "apps.market_data.scrapers.gumtree.GumtreeScraper",
    SourceSlug.IOL_PROPERTY:     "apps.market_data.scrapers.iol_property.IolPropertyScraper",
    SourceSlug.RENTFIND:         "apps.market_data.scrapers.rentfind.RentFindScraper",
    SourceSlug.PAM_GOLDING:      "apps.market_data.scrapers.pam_golding.PamGoldingScraper",
    SourceSlug.SEEFF:            "apps.market_data.scrapers.seeff.SeeffScraper",
    SourceSlug.FACEBOOK:         "apps.market_data.scrapers.facebook.FacebookScraper",
    SourceSlug.ANNA_BASSON:      "apps.market_data.scrapers.anna_basson.AnnaBossonScraper",
    SourceSlug.ENGEL_VOLKERS:    "apps.market_data.scrapers.engel_volkers.EngelVolkersScraper",
    SourceSlug.SOTHEBYS:         "apps.market_data.scrapers.sothebys.SothebysRealtyScraper",
    SourceSlug.CHAS_EVERITT:     "apps.market_data.scrapers.chas_everitt.ChasEverittScraper",
    SourceSlug.LOUW_COETZEE:     "apps.market_data.scrapers.louw_coetzee.LouwCoetzeeScraper",
}


def _import_scraper(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _upsert_agency(agency_dict: dict, source: str) -> ListingAgency | None:
    if not agency_dict:
        return None
    agent_id = agency_dict.get("source_agent_id") or ""
    if not agent_id:
        return None
    obj, _ = ListingAgency.objects.update_or_create(
        source=source,
        source_agent_id=agent_id,
        defaults={
            "agent_type": agency_dict.get("agent_type", "agency"),
            "name": agency_dict.get("name", ""),
            "agency_name": agency_dict.get("agency_name", ""),
            "phone": agency_dict.get("phone", ""),
            "email": agency_dict.get("email", ""),
            "profile_url": agency_dict.get("profile_url", ""),
            "photo_url": agency_dict.get("photo_url", ""),
            "agency_logo_url": agency_dict.get("agency_logo_url", ""),
            "raw_data": agency_dict,
        },
    )
    return obj


def _save_listing(item: dict, scrape_run: ScrapeRun, dry_run: bool) -> tuple[str, bool]:
    """
    Returns (action, is_new).
    action: 'saved', 'updated', 'skipped'
    """
    source = item["source"]
    source_listing_id = item["source_listing_id"]

    if dry_run:
        return "dry_run", False

    agency = _upsert_agency(item.get("agency"), source)

    # Determine active price for change tracking
    new_price = item.get("rental_price") or item.get("asking_price")

    try:
        existing = MarketListing.objects.get(source=source, source_listing_id=source_listing_id)
        # Check for price change
        old_price = existing.rental_price or existing.asking_price
        defaults = {
            "source_url": item.get("source_url", ""),
            "listing_type": item.get("listing_type", ""),
            "property_type": item.get("property_type", ""),
            "area": item.get("area", ""),
            "agency": agency,
            "asking_price": item.get("asking_price"),
            "rental_price": item.get("rental_price"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "floor_size_m2": item.get("floor_size_m2"),
            "erf_size_m2": item.get("erf_size_m2"),
            "parking": item.get("parking"),
            "is_furnished": item.get("is_furnished"),
            "pets_allowed": item.get("pets_allowed"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "raw_address": item.get("raw_address", ""),
            "suburb": item.get("suburb", ""),
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "listed_at": item.get("listed_at"),
            "scrape_run": scrape_run,
            "raw_data": item.get("raw_data", {}),
        }
        if new_price and old_price and float(new_price) != float(old_price):
            defaults["previous_price"] = old_price
            defaults["price_changed_at"] = timezone.now()

        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()

        # Add any new photos (don't delete existing)
        _save_photos(existing, item.get("photo_urls", []))
        return "updated", False

    except MarketListing.DoesNotExist:
        listing = MarketListing.objects.create(
            source=source,
            source_listing_id=source_listing_id,
            source_url=item.get("source_url", ""),
            listing_type=item.get("listing_type", ""),
            property_type=item.get("property_type", ""),
            area=item.get("area", ""),
            agency=agency,
            asking_price=item.get("asking_price"),
            rental_price=item.get("rental_price"),
            bedrooms=item.get("bedrooms"),
            bathrooms=item.get("bathrooms"),
            floor_size_m2=item.get("floor_size_m2"),
            erf_size_m2=item.get("erf_size_m2"),
            parking=item.get("parking"),
            is_furnished=item.get("is_furnished"),
            pets_allowed=item.get("pets_allowed"),
            latitude=item.get("latitude"),
            longitude=item.get("longitude"),
            raw_address=item.get("raw_address", ""),
            suburb=item.get("suburb", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            listed_at=item.get("listed_at"),
            scrape_run=scrape_run,
            raw_data=item.get("raw_data", {}),
        )
        _save_photos(listing, item.get("photo_urls", []))
        return "saved", True


def _save_photos(listing: MarketListing, photo_urls: list[str]):
    existing_urls = set(listing.photos.values_list("source_url", flat=True))
    for i, url in enumerate(photo_urls):
        if url and url not in existing_urls:
            MarketListingPhoto.objects.create(
                listing=listing,
                position=i,
                source_url=url,
            )


def _save_news(articles: list[dict], dry_run: bool) -> tuple[int, int]:
    saved = updated = 0
    for article in articles:
        if dry_run:
            saved += 1
            continue
        obj, created = AreaNewsArticle.objects.update_or_create(
            source_article_id=article["source_article_id"],
            defaults={
                "source": article["source"],
                "title": article["title"],
                "url": article["url"],
                "content_summary": article.get("content_summary", ""),
                "areas_mentioned": article.get("areas_mentioned", []),
                "topics": article.get("topics", []),
            },
        )
        if created:
            saved += 1
        else:
            updated += 1
    return saved, updated


def _save_bylaws(bylaw_items: list[dict], dry_run: bool) -> int:
    saved = 0
    for item in bylaw_items:
        if dry_run:
            saved += 1
            continue
        _, created = MunicipalBylaw.objects.get_or_create(
            source_url=item["source_url"],
            defaults={
                "municipality": item["municipality"],
                "title": item["title"],
                "category": item.get("category", "general"),
            },
        )
        if created:
            saved += 1
    return saved


class Command(BaseCommand):
    help = "Scrape property market data from configured sources"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="all",
            help="Source to scrape: property24|private_property|gumtree|iol_property|rentfind|pam_golding|seeff|anna_basson|engel_volkers|sothebys|chas_everitt|louw_coetzee|facebook|all",
        )
        parser.add_argument(
            "--area",
            default="all",
            help=f"Area slug or 'all'. Options: {', '.join(a.value for a in AreaSlug)}",
        )
        parser.add_argument(
            "--listing-type",
            default="both",
            help="rent|sale|both",
        )
        parser.add_argument("--news", action="store_true", help="Also scrape area news feeds")
        parser.add_argument("--bylaws", action="store_true", help="Also scrape municipal bylaws")
        parser.add_argument("--dry-run", action="store_true", help="Parse & print without saving to DB")

    def handle(self, *args, **options):
        source_opt = options["source"]
        area_opt = options["area"]
        listing_type_opt = options["listing_type"]
        do_news = options["news"]
        do_bylaws = options["bylaws"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be saved"))

        # Resolve sources
        if source_opt == "all":
            sources = ALL_SOURCES
        else:
            sources = [s for s in source_opt.split(",") if s.strip()]

        # Resolve areas
        all_area_values = [a.value for a in AreaSlug]
        if area_opt == "all":
            areas = all_area_values
        else:
            areas = [a.strip() for a in area_opt.split(",") if a.strip() in all_area_values]

        # Resolve listing types
        if listing_type_opt == "both":
            listing_types = [ListingType.RENT, ListingType.SALE]
        else:
            listing_types = [listing_type_opt]

        summary_rows = []

        for source in sources:
            scraper_path = SCRAPER_MAP.get(source)
            if not scraper_path:
                self.stdout.write(self.style.ERROR(f"Unknown source: {source}"))
                continue

            ScraperClass = _import_scraper(scraper_path)
            scraper = ScraperClass()

            for area in areas:
                for listing_type in listing_types:
                    run = None if dry_run else ScrapeRun.objects.create(
                        source=source,
                        area=area,
                        listing_type=listing_type,
                    )

                    self.stdout.write(f"  → {source}/{area}/{listing_type} ...", ending="")
                    start = datetime.now()
                    saved = updated = skipped = found = 0
                    error_msg = ""

                    try:
                        listings = scraper.scrape(area, listing_type)
                        found = len(listings)

                        for item in listings:
                            action, _ = _save_listing(item, run, dry_run)
                            if action == "saved":
                                saved += 1
                            elif action == "updated":
                                updated += 1
                            else:
                                skipped += 1

                        status = ScrapeRun.Status.SUCCESS

                    except Exception as e:
                        error_msg = str(e)
                        status = ScrapeRun.Status.FAILED
                        if options.get("verbosity", 1) >= 2:
                            self.stdout.write(traceback.format_exc())

                    elapsed = (datetime.now() - start).total_seconds()

                    if run:
                        run.listings_found = found
                        run.listings_saved = saved
                        run.listings_updated = updated
                        run.listings_skipped = skipped
                        run.mark_done(status, error_msg)

                    row_status = "✓" if status == ScrapeRun.Status.SUCCESS else "✗"
                    self.stdout.write(
                        f" {row_status} found={found} saved={saved} updated={updated} ({elapsed:.1f}s)"
                    )
                    if error_msg:
                        self.stdout.write(self.style.ERROR(f"     Error: {error_msg}"))

                    summary_rows.append((source, area, listing_type, found, saved, updated, elapsed, status))

        # News
        if do_news:
            self.stdout.write("\nScraping news feeds...")
            from apps.market_data.scrapers.news import scrape_news_feeds
            articles = scrape_news_feeds()
            news_saved, news_updated = _save_news(articles, dry_run)
            self.stdout.write(f"  News: found={len(articles)} saved={news_saved} updated={news_updated}")

        # Bylaws
        if do_bylaws:
            self.stdout.write("\nScraping bylaws...")
            from apps.market_data.scrapers.bylaws import scrape_bylaws
            bylaw_items = scrape_bylaws()
            bylaws_saved = _save_bylaws(bylaw_items, dry_run)
            self.stdout.write(f"  Bylaws: found={len(bylaw_items)} saved={bylaws_saved}")

        # Refresh daily stats
        if not dry_run and summary_rows:
            self.stdout.write("\nRefreshing price stats...")
            MarketPriceStats.refresh_for_date(date.today())
            self.stdout.write(self.style.SUCCESS("  Done."))

        # Summary table
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(f"{'Source':<18} {'Area':<22} {'Type':<6} {'Found':>6} {'Saved':>6} {'Upd':>5}")
        self.stdout.write("-" * 70)
        for row in summary_rows:
            source, area, lt, found, saved, updated, elapsed, status = row
            self.stdout.write(f"{source:<18} {area:<22} {lt:<6} {found:>6} {saved:>6} {updated:>5}")
        self.stdout.write("=" * 70)

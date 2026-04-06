"""
Enrich market listings with Google Maps data and ChromaDB vectorization.

Usage:
  python manage.py enrich_market_listings
  python manage.py enrich_market_listings --area stellenbosch --limit 50
  python manage.py enrich_market_listings --listing-id 42
  python manage.py enrich_market_listings --skip-streetview --skip-places
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.market_data.models import (
    AreaSlug,
    ListingNearbyPlace,
    ListingStreetView,
    MarketListing,
)
from apps.market_data.services.google_maps import GoogleMapsService

logger = logging.getLogger(__name__)


def _build_embedding_text(listing: MarketListing) -> str:
    price_part = ""
    if listing.rental_price:
        price_part = f"Monthly rent R{listing.rental_price:,.0f}."
    elif listing.asking_price:
        price_part = f"Asking price R{listing.asking_price:,.0f}."

    size_part = ""
    if listing.floor_size_m2:
        size_part = f"Floor size {listing.floor_size_m2}m²."

    amenity_names = list(
        listing.nearby_places.order_by("distance_m").values_list("name", flat=True)[:10]
    )
    amenity_part = f"Nearby: {', '.join(amenity_names)}." if amenity_names else ""

    return (
        f"{listing.get_property_type_display() or 'Property'} "
        f"{'with ' + str(listing.bedrooms) + ' bedrooms' if listing.bedrooms else ''} "
        f"in {listing.suburb or listing.get_area_display()}. "
        f"{price_part} "
        f"{size_part} "
        f"{listing.title}. "
        f"{(listing.description or '')[:600]}. "
        f"{amenity_part}"
    ).strip()


def _upsert_to_chromadb(listing: MarketListing, text: str):
    try:
        from core.contract_rag import get_market_listings_collection
        collection = get_market_listings_collection()
        meta = {
            "listing_id": listing.pk,
            "source": listing.source,
            "area": listing.area,
            "listing_type": listing.listing_type,
            "property_type": listing.property_type or "",
            "bedrooms": listing.bedrooms or 0,
            "price": float(listing.rental_price or listing.asking_price or 0),
            "suburb": listing.suburb or "",
        }
        if listing.latitude:
            meta["latitude"] = listing.latitude
        if listing.longitude:
            meta["longitude"] = listing.longitude
        collection.upsert(
            ids=[str(listing.pk)],
            documents=[text],
            metadatas=[meta],
        )
    except Exception as e:
        logger.warning("ChromaDB upsert failed for listing %s: %s", listing.pk, e)


class Command(BaseCommand):
    help = "Enrich market listings with Google Street View, nearby places, and vector embeddings"

    def add_arguments(self, parser):
        parser.add_argument("--listing-id", type=int, help="Enrich a specific listing by ID")
        parser.add_argument("--area", help="Filter by area slug")
        parser.add_argument("--limit", type=int, default=100, help="Max listings to enrich per run")
        parser.add_argument("--skip-streetview", action="store_true")
        parser.add_argument("--skip-places", action="store_true")
        parser.add_argument("--skip-vectorize", action="store_true")

    def handle(self, *args, **options):
        listing_id = options.get("listing_id")
        area = options.get("area")
        limit = options["limit"]
        skip_sv = options["skip_streetview"]
        skip_places = options["skip_places"]
        skip_vec = options["skip_vectorize"]

        maps = GoogleMapsService()

        if not maps.available and not (skip_sv and skip_places):
            self.stdout.write(self.style.WARNING(
                "GOOGLE_MAPS_API_KEY not set — Street View and Places will be skipped. "
                "Use --skip-streetview --skip-places to suppress this warning."
            ))
            skip_sv = True
            skip_places = True

        # Build queryset
        if listing_id:
            qs = MarketListing.objects.filter(pk=listing_id)
        else:
            qs = MarketListing.objects.filter(enriched_at__isnull=True)
            if area:
                qs = qs.filter(area=area)
            # Prioritise listings with coordinates (most useful to enrich)
            qs = qs.filter(latitude__isnull=False).order_by("-first_seen_at")[:limit]

        total = qs.count()
        self.stdout.write(f"Enriching {total} listings...")
        enriched = failed = streetview_ok = places_ok = vectorized = 0

        for listing in qs.iterator():
            lat, lng = listing.latitude, listing.longitude
            self.stdout.write(f"  [{listing.pk}] {listing.suburb or listing.area} ...", ending="")

            try:
                # --- Street View ---
                if not skip_sv and lat and lng and not hasattr(listing, "street_view"):
                    photo_bytes, api_status = maps.fetch_street_view(lat, lng)
                    sv, _ = ListingStreetView.objects.get_or_create(
                        listing=listing,
                        defaults={"api_status": api_status},
                    )
                    if photo_bytes:
                        from django.core.files.base import ContentFile
                        sv.photo_file.save(
                            f"sv_{listing.pk}.jpg",
                            ContentFile(photo_bytes),
                            save=True,
                        )
                        sv.api_status = api_status
                        sv.save(update_fields=["api_status"])
                        streetview_ok += 1

                # --- Nearby Places ---
                if not skip_places and lat and lng:
                    if not listing.nearby_places.exists():
                        place_dicts = maps.enrich_listing_places(lat, lng)
                        for pd in place_dicts:
                            ListingNearbyPlace.objects.get_or_create(
                                listing=listing,
                                place_id=pd["place_id"],
                                defaults={
                                    "name": pd["name"],
                                    "category": pd["category"],
                                    "place_type": pd.get("place_type", ""),
                                    "distance_m": pd.get("distance_m"),
                                    "drive_minutes": pd.get("drive_minutes"),
                                    "walk_minutes": pd.get("walk_minutes"),
                                    "latitude": pd.get("latitude"),
                                    "longitude": pd.get("longitude"),
                                    "rating": pd.get("rating"),
                                },
                            )
                        places_ok += 1

                # --- Vectorize ---
                if not skip_vec:
                    text = _build_embedding_text(listing)
                    _upsert_to_chromadb(listing, text)
                    vectorized += 1

                listing.enriched_at = timezone.now()
                listing.save(update_fields=["enriched_at"])
                enriched += 1
                self.stdout.write(" ✓")

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f" ✗ {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. enriched={enriched} failed={failed} "
            f"streetview={streetview_ok} places={places_ok} vectorized={vectorized}"
        ))

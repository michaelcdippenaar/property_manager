"""
Download property listing photos and agent/agency photos to local storage.

Usage:
  python manage.py download_market_photos
  python manage.py download_market_photos --listing-id 42
  python manage.py download_market_photos --limit 200
  python manage.py download_market_photos --agents-only
"""
from __future__ import annotations

import io
import time
from datetime import datetime
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.market_data.models import ListingAgency, MarketListingPhoto


class Command(BaseCommand):
    help = "Download property listing and agent photos to local media storage"

    def add_arguments(self, parser):
        parser.add_argument("--listing-id", type=int, help="Download photos for a specific listing only")
        parser.add_argument("--limit", type=int, default=200, help="Max photos to download per run")
        parser.add_argument("--agents-only", action="store_true", help="Only download agent/agency photos")
        parser.add_argument("--delay", type=float, default=0.5, help="Seconds between downloads")

    def handle(self, *args, **options):
        listing_id = options.get("listing_id")
        limit = options["limit"]
        agents_only = options["agents_only"]
        delay = options["delay"]

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; TremlyMarketBot/1.0)"
        })

        downloaded = failed = skipped = 0

        if not agents_only:
            # Listing photos
            photo_qs = MarketListingPhoto.objects.filter(is_downloaded=False).exclude(source_url="")
            if listing_id:
                photo_qs = photo_qs.filter(listing_id=listing_id)
            photo_qs = photo_qs.select_related("listing").order_by("listing_id", "position")[:limit]

            self.stdout.write(f"Downloading {photo_qs.count()} listing photos...")
            for photo in photo_qs:
                try:
                    resp = session.get(photo.source_url, timeout=15)
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1].split(";")[0].strip()
                    filename = f"listing_{photo.listing_id}_p{photo.position}.{ext}"

                    photo.photo_file.save(filename, ContentFile(resp.content), save=False)
                    photo.is_downloaded = True
                    photo.downloaded_at = timezone.now()

                    # Try to get dimensions
                    try:
                        from PIL import Image
                        img = Image.open(io.BytesIO(resp.content))
                        photo.width_px, photo.height_px = img.size
                    except Exception:
                        pass

                    photo.save(update_fields=["photo_file", "is_downloaded", "downloaded_at", "width_px", "height_px"])
                    downloaded += 1
                    time.sleep(delay)

                except Exception as e:
                    failed += 1
                    if options.get("verbosity", 1) >= 2:
                        self.stdout.write(self.style.WARNING(f"  Failed {photo.source_url}: {e}"))

        # Agent / agency photos
        agent_qs = ListingAgency.objects.filter(photo_file="").exclude(photo_url="")
        self.stdout.write(f"Downloading {agent_qs.count()} agent photos...")
        for agent in agent_qs[:limit]:
            try:
                resp = session.get(agent.photo_url, timeout=15)
                resp.raise_for_status()
                ext = resp.headers.get("content-type", "image/jpeg").split("/")[-1].split(";")[0].strip()
                filename = f"agent_{agent.pk}.{ext}"
                agent.photo_file.save(filename, ContentFile(resp.content), save=False)
                agent.save(update_fields=["photo_file"])
                downloaded += 1
                time.sleep(delay)
            except Exception as e:
                failed += 1

        # Agency logos
        logo_qs = ListingAgency.objects.filter(agency_logo_file="").exclude(agency_logo_url="")
        self.stdout.write(f"Downloading {logo_qs.count()} agency logos...")
        for agency in logo_qs[:limit]:
            try:
                resp = session.get(agency.agency_logo_url, timeout=15)
                resp.raise_for_status()
                ext = resp.headers.get("content-type", "image/png").split("/")[-1].split(";")[0].strip()
                filename = f"agency_{agency.pk}.{ext}"
                agency.agency_logo_file.save(filename, ContentFile(resp.content), save=False)
                agency.save(update_fields=["agency_logo_file"])
                downloaded += 1
                time.sleep(delay)
            except Exception as e:
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. downloaded={downloaded} failed={failed}"
        ))

"""
Facebook Marketplace / Groups scraper — OPTIONAL.

Requires:
  pip install playwright
  python -m playwright install chromium

  A valid Facebook session file at backend/fb_session.json (cookies exported after manual login).

Usage:
  python manage.py scrape_market_data --source facebook --area stellenbosch --listing-type rent

Facebook actively blocks automated scraping. This scraper:
  - Uses Playwright with a stored cookie session to avoid login prompts
  - Navigates to Marketplace with location filters
  - Is disabled by default — only runs when explicitly requested via --source facebook

Session renewal: If scraping fails due to session expiry, log into Facebook manually,
export cookies to backend/fb_session.json using a browser extension (e.g. Cookie-Editor),
and re-run.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

SESSION_FILE = Path(__file__).parents[4] / "fb_session.json"

AREA_MARKETPLACE_LOCATIONS: dict[str, dict] = {
    AreaSlug.CITY_BOWL: {"city": "Cape Town", "radius": 5},
    AreaSlug.ATLANTIC_SEABOARD: {"city": "Cape Town", "radius": 3},
    AreaSlug.SOUTHERN_SUBURBS: {"city": "Claremont", "radius": 5},
    AreaSlug.NORTHERN_SUBURBS_CPT: {"city": "Bellville", "radius": 10},
    AreaSlug.HELDERBERG: {"city": "Somerset West", "radius": 10},
    AreaSlug.FALSE_BAY: {"city": "Fish Hoek", "radius": 10},
    AreaSlug.HOUT_BAY: {"city": "Hout Bay", "radius": 5},
    AreaSlug.STELLENBOSCH: {"city": "Stellenbosch", "radius": 10},
    AreaSlug.PAARL: {"city": "Paarl", "radius": 10},
    AreaSlug.FRANSCHHOEK: {"city": "Franschhoek", "radius": 5},
    AreaSlug.SOMERSET_WEST: {"city": "Somerset West", "radius": 10},
    AreaSlug.STRAND: {"city": "Strand", "radius": 5},
}

# Facebook property groups to also scrape (supplement Marketplace)
FB_PROPERTY_GROUPS = [
    "https://www.facebook.com/groups/stellenboschproperty",
    "https://www.facebook.com/groups/capetownpropertyrental",
    "https://www.facebook.com/groups/winaldspropertyforsale",
]


class FacebookScraper(BaseScraper):
    source = SourceSlug.FACEBOOK
    RATE_LIMIT_SECONDS = 3.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return AREA_MARKETPLACE_LOCATIONS.get(area, {})

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log("playwright not installed. Run: pip install playwright && python -m playwright install chromium", "error")
            return []

        if not SESSION_FILE.exists():
            self.log(
                f"Facebook session file not found at {SESSION_FILE}. "
                "Log in manually and export cookies using a browser extension.",
                "error",
            )
            return []

        location = AREA_MARKETPLACE_LOCATIONS.get(area, {})
        if not location:
            return []

        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Load saved cookies
            try:
                with open(SESSION_FILE) as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
            except Exception as e:
                self.log(f"Failed to load FB session: {e}", "error")
                browser.close()
                return []

            page = context.new_page()
            try:
                results.extend(self._scrape_marketplace(page, area, listing_type, location))
            except Exception as e:
                self.log(f"Marketplace scraping failed: {e}", "warning")

            browser.close()

        return results

    def _scrape_marketplace(self, page, area: str, listing_type: str, location: dict) -> list[dict[str, Any]]:
        category = "propertyrentals" if listing_type == ListingType.RENT else "propertyforsale"
        city = location.get("city", "Cape Town").replace(" ", "%20")
        url = f"https://www.facebook.com/marketplace/{city.lower().replace('%20', '-')}/{category}"

        self.log(f"Navigating to {url}")
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Scroll to load more listings
        for _ in range(3):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(1500)

        # Extract listing cards
        cards = page.query_selector_all("[data-testid='marketplace_feed_item'], article[role='article']")
        results = []

        for card in cards[:50]:  # Cap at 50 per area/type
            try:
                parsed = self._parse_card(card, page, area, listing_type)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                self.log(f"Error parsing card: {e}", "warning")

        return results

    def _parse_card(self, card, page, area: str, listing_type: str) -> dict | None:
        import re

        link_el = card.query_selector("a[href*='/marketplace/item/']")
        if not link_el:
            return None

        href = link_el.get_attribute("href") or ""
        id_match = re.search(r"/item/(\d+)", href)
        listing_id = id_match.group(1) if id_match else None
        if not listing_id:
            return None

        full_url = f"https://www.facebook.com{href}" if not href.startswith("http") else href

        title_el = card.query_selector("[data-testid='marketplace_listing_title'], h2, h3")
        title = title_el.inner_text() if title_el else ""

        price_el = card.query_selector("[data-testid='marketplace_listing_price']")
        price_text = price_el.inner_text() if price_el else ""
        price = self._safe_price(price_text)

        img_el = card.query_selector("img")
        photo_url = img_el.get_attribute("src") if img_el else ""

        bed_match = re.search(r"(\d+)\s*(?:bed|br)", title, re.I)
        bedrooms = int(bed_match.group(1)) if bed_match else None

        return {
            "source": SourceSlug.FACEBOOK,
            "source_listing_id": listing_id,
            "source_url": full_url,
            "listing_type": listing_type,
            "property_type": PropertyType.OTHER,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": bedrooms,
            "bathrooms": None,
            "floor_size_m2": None,
            "erf_size_m2": None,
            "parking": None,
            "latitude": None,
            "longitude": None,
            "raw_address": "",
            "suburb": "",
            "title": title,
            "description": "",
            "photo_urls": [photo_url] if photo_url else [],
            "agency": None,
            "raw_data": {},
        }

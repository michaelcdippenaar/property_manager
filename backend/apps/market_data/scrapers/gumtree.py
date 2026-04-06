"""
Gumtree.co.za scraper — HTML scraping for property listings.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Map AreaSlug → (search_term, location_id) for Gumtree URLs
AREA_MAP: dict[str, list[tuple[str, str]]] = {
    AreaSlug.CITY_BOWL: [("cape-town-city-bowl", "1010049")],
    AreaSlug.ATLANTIC_SEABOARD: [("camps-bay", "1010052"), ("sea-point", "1010065")],
    AreaSlug.SOUTHERN_SUBURBS: [("southern-suburbs-cape-town", "1010066")],
    AreaSlug.NORTHERN_SUBURBS_CPT: [("bellville", "1010037"), ("durbanville", "1010041")],
    AreaSlug.HELDERBERG: [("somerset-west", "1010067"), ("strand", "1010068")],
    AreaSlug.FALSE_BAY: [("fish-hoek", "1010043"), ("muizenberg", "1010057")],
    AreaSlug.HOUT_BAY: [("hout-bay", "1010047")],
    AreaSlug.STELLENBOSCH: [("stellenbosch", "1010115")],
    AreaSlug.PAARL: [("paarl", "1010113")],
    AreaSlug.FRANSCHHOEK: [("franschhoek", "1010109")],
    AreaSlug.SOMERSET_WEST: [("somerset-west", "1010067")],
    AreaSlug.STRAND: [("strand", "1010068")],
}

# Gumtree category codes: 9262 = property to let, 9263 = property for sale
CATEGORY_MAP = {
    ListingType.RENT: "9262",
    ListingType.SALE: "9263",
}


class GumtreeScraper(BaseScraper):
    source = SourceSlug.GUMTREE
    BASE_URL = "https://www.gumtree.co.za"
    RATE_LIMIT_SECONDS = 2.5

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"locations": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — skipping Gumtree", "warning")
            return []

        category_id = CATEGORY_MAP.get(listing_type, "9262")
        locations = AREA_MAP.get(area, [])
        results = []

        for location_slug, location_id in locations:
            self.log(f"Scraping {location_slug} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                url = (
                    f"{self.BASE_URL}/s-property-{'to-let' if listing_type == ListingType.RENT else 'for-sale'}"
                    f"/{location_slug}"
                    f"/k0c{category_id}l{location_id}"
                    f"{'?page=' + str(page) if page > 1 else ''}"
                )
                try:
                    resp = self.get(url)
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = self._parse_page(soup, listing_type, area)
                    if not listings:
                        break
                    results.extend(listings)
                    # Check for next page link
                    next_link = soup.select_one("a[data-testid='pagination-next']") or soup.select_one(".pagination-next a")
                    if not next_link:
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {url}: {e}", "warning")
                    break

        return results

    def _parse_page(self, soup, listing_type: str, area: str) -> list[dict[str, Any]]:
        cards = (
            soup.select("article[data-testid='listing']")
            or soup.select(".listing-results article")
            or soup.select(".results li.result-list-item")
        )
        results = []
        for card in cards:
            parsed = self._parse_card(card, listing_type, area)
            if parsed:
                results.append(parsed)
        return results

    def _parse_card(self, card, listing_type: str, area: str) -> dict | None:
        link_el = card.select_one("a[href*='/a-']") or card.select_one("a.listing-title") or card.select_one("h2 a")
        if not link_el:
            return None

        href = link_el.get("href", "")
        listing_id_match = re.search(r"/a-[^/]+/(\d+)", href)
        listing_id = listing_id_match.group(1) if listing_id_match else hashlib.md5(href.encode()).hexdigest()[:16]

        full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
        title = link_el.get_text(strip=True) or card.select_one("h2, h3")

        price_el = card.select_one("[data-testid='price']") or card.select_one(".price")
        price = self._safe_price(price_el.get_text(strip=True) if price_el else None)

        desc_el = card.select_one("[data-testid='description']") or card.select_one(".description")
        description = desc_el.get_text(strip=True) if desc_el else ""

        location_el = card.select_one("[data-testid='location']") or card.select_one(".location")
        raw_address = location_el.get_text(strip=True) if location_el else ""

        img_el = card.select_one("img[src*='gumtree']") or card.select_one("img")
        photo_urls = []
        if img_el:
            src = img_el.get("src") or img_el.get("data-src") or ""
            if src and not src.endswith("placeholder"):
                photo_urls.append(src)

        # Extract bedrooms from title/description
        bed_match = re.search(r"(\d+)\s*(?:bed(?:room)?s?|br)", (title or "") + " " + description, re.I)
        bedrooms = int(bed_match.group(1)) if bed_match else None

        return {
            "source": SourceSlug.GUMTREE,
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
            "raw_address": raw_address,
            "suburb": "",
            "title": str(title or ""),
            "description": description,
            "photo_urls": photo_urls,
            "agency": None,
            "raw_data": {},
        }

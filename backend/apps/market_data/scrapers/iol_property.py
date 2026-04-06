"""
IOL Property scraper — HTML scraping of iol.co.za/property.
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

AREA_MAP: dict[str, list[str]] = {
    AreaSlug.CITY_BOWL: ["cape-town-city-bowl-city-centre"],
    AreaSlug.ATLANTIC_SEABOARD: ["camps-bay", "sea-point", "clifton"],
    AreaSlug.SOUTHERN_SUBURBS: ["southern-suburbs-cape-town"],
    AreaSlug.NORTHERN_SUBURBS_CPT: ["bellville", "durbanville"],
    AreaSlug.HELDERBERG: ["somerset-west", "strand"],
    AreaSlug.FALSE_BAY: ["fish-hoek", "muizenberg"],
    AreaSlug.HOUT_BAY: ["hout-bay"],
    AreaSlug.STELLENBOSCH: ["stellenbosch"],
    AreaSlug.PAARL: ["paarl"],
    AreaSlug.FRANSCHHOEK: ["franschhoek"],
    AreaSlug.SOMERSET_WEST: ["somerset-west"],
    AreaSlug.STRAND: ["strand"],
}


class IolPropertyScraper(BaseScraper):
    source = SourceSlug.IOL_PROPERTY
    BASE_URL = "https://www.iol.co.za"
    RATE_LIMIT_SECONDS = 2.5

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — skipping IOL", "warning")
            return []

        segment = "rent" if listing_type == ListingType.RENT else "for-sale"
        suburbs = AREA_MAP.get(area, [])
        results = []

        for suburb_slug in suburbs:
            self.log(f"Scraping {suburb_slug} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                url = f"{self.BASE_URL}/property/{segment}/{suburb_slug}?page={page}"
                try:
                    resp = self.get(url)
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = self._parse_page(soup, listing_type, area, suburb_slug)
                    if not listings:
                        break
                    results.extend(listings)
                    next_link = soup.select_one("a.pagination__next") or soup.select_one("[aria-label='Next page']")
                    if not next_link:
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {url}: {e}", "warning")
                    break

        return results

    def _parse_page(self, soup, listing_type: str, area: str, suburb_slug: str) -> list[dict[str, Any]]:
        cards = soup.select(".property-card, .listing-card, article.property")
        results = []
        for card in cards:
            parsed = self._parse_card(card, listing_type, area, suburb_slug)
            if parsed:
                results.append(parsed)
        return results

    def _parse_card(self, card, listing_type: str, area: str, suburb_slug: str) -> dict | None:
        link_el = card.select_one("a[href*='/property/']") or card.select_one("h2 a, h3 a")
        if not link_el:
            return None

        href = link_el.get("href", "")
        id_match = re.search(r"/(\d+)/?$", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]

        full_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
        title = link_el.get_text(strip=True) or ""

        price_el = card.select_one(".price, [class*='price']")
        price = self._safe_price(price_el.get_text(strip=True) if price_el else None)

        beds_el = card.select_one("[class*='bedroom'], [data-beds]")
        bedrooms = self._safe_int(beds_el.get_text(strip=True) if beds_el else None) if beds_el else None

        baths_el = card.select_one("[class*='bathroom'], [data-baths]")
        bathrooms = self._safe_float(baths_el.get_text(strip=True) if baths_el else None) if baths_el else None

        area_el = card.select_one("[class*='area'], [class*='size']")
        floor_size = self._safe_float(area_el.get_text(strip=True).replace("m²", "") if area_el else None) if area_el else None

        addr_el = card.select_one("[class*='address'], [class*='location']")
        raw_address = addr_el.get_text(strip=True) if addr_el else suburb_slug.replace("-", " ").title()

        img_el = card.select_one("img")
        photo_urls = []
        if img_el:
            src = img_el.get("src") or img_el.get("data-src") or ""
            if src:
                photo_urls.append(src)

        return {
            "source": SourceSlug.IOL_PROPERTY,
            "source_listing_id": listing_id,
            "source_url": full_url,
            "listing_type": listing_type,
            "property_type": PropertyType.OTHER,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floor_size_m2": floor_size,
            "erf_size_m2": None,
            "parking": None,
            "latitude": None,
            "longitude": None,
            "raw_address": raw_address,
            "suburb": suburb_slug.replace("-", " ").title(),
            "title": title,
            "description": "",
            "photo_urls": photo_urls,
            "agency": None,
            "raw_data": {},
        }

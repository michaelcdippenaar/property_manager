"""
RentFind.co.za scraper — HTML scraping for rental listings.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from urllib.parse import urlencode

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

AREA_MAP: dict[str, list[tuple[str, str]]] = {
    AreaSlug.CITY_BOWL: [("Cape Town City Bowl", "CT")],
    AreaSlug.ATLANTIC_SEABOARD: [("Atlantic Seaboard", "CT"), ("Camps Bay", "CT")],
    AreaSlug.SOUTHERN_SUBURBS: [("Southern Suburbs Cape Town", "CT")],
    AreaSlug.NORTHERN_SUBURBS_CPT: [("Bellville", "CT"), ("Durbanville", "CT")],
    AreaSlug.HELDERBERG: [("Somerset West", "CT"), ("Strand", "CT")],
    AreaSlug.FALSE_BAY: [("Fish Hoek", "CT"), ("Muizenberg", "CT")],
    AreaSlug.HOUT_BAY: [("Hout Bay", "CT")],
    AreaSlug.STELLENBOSCH: [("Stellenbosch", "WC")],
    AreaSlug.PAARL: [("Paarl", "WC")],
    AreaSlug.FRANSCHHOEK: [("Franschhoek", "WC")],
    AreaSlug.SOMERSET_WEST: [("Somerset West", "CT")],
    AreaSlug.STRAND: [("Strand", "CT")],
}


class RentFindScraper(BaseScraper):
    source = SourceSlug.RENTFIND
    BASE_URL = "https://www.rentfind.co.za"
    RESULTS_URL = "https://www.rentfind.co.za/Properties/Results.aspx"
    RATE_LIMIT_SECONDS = 2.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"locations": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if listing_type == ListingType.SALE:
            self.log("RentFind is rental-only, skipping sale listings")
            return []

        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — skipping RentFind", "warning")
            return []

        locations = AREA_MAP.get(area, [])
        results = []

        for suburb_name, province in locations:
            self.log(f"Scraping {suburb_name}")
            page = 1
            while page <= self.MAX_PAGES:
                params = {
                    "suburb": suburb_name,
                    "province": province,
                    "page": page,
                }
                url = f"{self.RESULTS_URL}?{urlencode(params)}"
                try:
                    resp = self.get(url)
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = self._parse_page(soup, area, suburb_name)
                    if not listings:
                        break
                    results.extend(listings)
                    next_link = soup.select_one("a.next, a[rel='next'], .pagination a:last-child")
                    if not next_link or "disabled" in (next_link.get("class") or []):
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {suburb_name} page {page}: {e}", "warning")
                    break

        return results

    def _parse_page(self, soup, area: str, suburb_name: str) -> list[dict[str, Any]]:
        cards = soup.select(".property-item, .listing, .property-listing, .results-item")
        results = []
        for card in cards:
            parsed = self._parse_card(card, area, suburb_name)
            if parsed:
                results.append(parsed)
        return results

    def _parse_card(self, card, area: str, suburb_name: str) -> dict | None:
        link_el = card.select_one("a[href]")
        if not link_el:
            return None

        href = link_el.get("href", "")
        id_match = re.search(r"[Ii]d=(\d+)", href) or re.search(r"/(\d+)/?", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]

        full_url = href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
        title = (card.select_one("h2, h3, .title") or link_el).get_text(strip=True)

        price_el = card.select_one(".price, [class*='price'], .rent")
        price = self._safe_price(price_el.get_text(strip=True) if price_el else None)

        beds_el = card.select_one("[class*='bed'], .bedrooms")
        bedrooms = self._safe_int(re.search(r"\d+", beds_el.get_text()) .group() if beds_el else None) if beds_el else None

        baths_el = card.select_one("[class*='bath'], .bathrooms")
        bathrooms = self._safe_float(re.search(r"[\d.]+", baths_el.get_text()).group() if baths_el else None) if baths_el else None

        img_el = card.select_one("img")
        photo_urls = []
        if img_el:
            src = img_el.get("src") or img_el.get("data-src") or ""
            if src:
                photo_urls.append(src if src.startswith("http") else f"{self.BASE_URL}/{src.lstrip('/')}")

        return {
            "source": SourceSlug.RENTFIND,
            "source_listing_id": listing_id,
            "source_url": full_url,
            "listing_type": ListingType.RENT,
            "property_type": PropertyType.OTHER,
            "area": area,
            "asking_price": None,
            "rental_price": price,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floor_size_m2": None,
            "erf_size_m2": None,
            "parking": None,
            "latitude": None,
            "longitude": None,
            "raw_address": suburb_name,
            "suburb": suburb_name,
            "title": title,
            "description": "",
            "photo_urls": photo_urls,
            "agency": None,
            "raw_data": {},
        }

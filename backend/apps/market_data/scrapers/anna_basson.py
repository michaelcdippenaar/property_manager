"""
Anna Basson Eiendomme scraper — Stellenbosch-based boutique agency.
Website: https://annabasson.co.za
Strategy: server-rendered HTML, BeautifulSoup.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

# Anna Basson operates exclusively in the Winelands / Stellenbosch area.
AREA_MAP: dict[str, list[str]] = {
    AreaSlug.STELLENBOSCH: ["stellenbosch"],
    AreaSlug.FRANSCHHOEK:  ["franschhoek"],
    AreaSlug.PAARL:        ["paarl"],
    AreaSlug.SOMERSET_WEST: ["somerset-west"],
    AreaSlug.STRAND:       ["strand"],
}

PROPERTY_TYPE_MAP = {
    "apartment":  PropertyType.APARTMENT,
    "flat":       PropertyType.APARTMENT,
    "house":      PropertyType.HOUSE,
    "townhouse":  PropertyType.TOWNHOUSE,
    "simplex":    PropertyType.SIMPLEX,
    "duplex":     PropertyType.DUPLEX,
    "studio":     PropertyType.STUDIO,
    "bachelor":   PropertyType.BACHELOR,
    "farm":       PropertyType.FARM,
    "plot":       PropertyType.PLOT,
    "vacant land": PropertyType.PLOT,
    "commercial": PropertyType.COMMERCIAL,
}


def _detect_property_type(text: str) -> str:
    text_lower = text.lower()
    for keyword, ptype in PROPERTY_TYPE_MAP.items():
        if keyword in text_lower:
            return ptype
    return PropertyType.OTHER


class AnnaBossonScraper(BaseScraper):
    source = SourceSlug.ANNA_BASSON
    BASE_URL = "https://annabasson.co.za"
    RATE_LIMIT_SECONDS = 2.5

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"areas": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — cannot scrape Anna Basson", "error")
            return []

        if area not in AREA_MAP:
            return []

        listing_param = "rental" if listing_type == ListingType.RENT else "sale"
        results = []

        # Try suburb-filtered search first; fall back to unfiltered listing page
        area_slugs = AREA_MAP[area]
        for area_slug in area_slugs:
            self.log(f"Scraping {area_slug} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                url = f"{self.BASE_URL}/properties/"
                params = {
                    "type": listing_param,
                    "area": area_slug,
                    "page": page,
                }
                try:
                    resp = self.get(url, params=params)
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = self._parse_page(soup, listing_type, area)
                    if not listings:
                        # Try without area filter on page 1 to check if the site uses different params
                        if page == 1:
                            resp2 = self.get(f"{self.BASE_URL}/properties/", params={"type": listing_param, "page": page})
                            soup2 = BeautifulSoup(resp2.text, "lxml")
                            listings = self._parse_page(soup2, listing_type, area)
                        if not listings:
                            break
                    results.extend(listings)

                    # Pagination — look for next page link
                    next_link = soup.select_one("a.next, a[rel='next'], .pagination a:last-child")
                    if not next_link or len(listings) < 12:
                        break
                    page += 1

                except Exception as e:
                    self.log(f"Error scraping {url}: {e}", "warning")
                    break

        return results

    def _parse_page(self, soup, listing_type: str, area: str) -> list[dict[str, Any]]:
        # Common card selectors used by South African property sites
        cards = (
            soup.select(".card-property")
            or soup.select(".property-card")
            or soup.select(".listing-card")
            or soup.select("article.property")
            or soup.select(".property-item")
            or soup.select("[class*='property'][class*='card']")
        )
        results = []
        for card in cards:
            parsed = self._parse_card(card, listing_type, area)
            if parsed:
                results.append(parsed)
        return results

    def _parse_card(self, card, listing_type: str, area: str) -> dict | None:
        # Extract listing ID from href or data attribute
        link_el = card.select_one("a[href*='/properties/']") or card.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        # Derive ID from URL or generate hash
        id_match = re.search(r"/properties/(?:details/)?(\d+|[\w-]+)/?", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]
        if not listing_id:
            return None

        # Title
        title_el = card.select_one("h2, h3, .property-title, .card-title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""
        prop_type = _detect_property_type(title)

        # Price
        price_el = card.select_one(".price, .property-price, [class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = self._safe_price(price_text)

        # Location / suburb
        loc_el = card.select_one(".location, .suburb, .address, [class*='location'], [class*='suburb']")
        suburb = loc_el.get_text(strip=True) if loc_el else ""

        # Bedrooms / bathrooms — look for feature icons or text
        beds = baths = None
        bed_el = card.select_one("[class*='bed'], .bedrooms, .beds")
        bath_el = card.select_one("[class*='bath'], .bathrooms, .baths")
        if bed_el:
            beds = self._safe_int(re.sub(r"[^\d]", "", bed_el.get_text(strip=True)))
        if bath_el:
            baths = self._safe_float(re.sub(r"[^\d.]", "", bath_el.get_text(strip=True)))

        # Floor size
        size_el = card.select_one("[class*='size'], [class*='floor'], .erf")
        floor_size = None
        if size_el:
            floor_size = self._safe_float(size_el.get_text(strip=True).replace("m²", "").replace("sqm", ""))

        # Images — Cloudinary CDN used by annabasson.co.za
        photo_urls = []
        for img in card.select("img[src], img[data-src], img[lazy-src]"):
            src = img.get("data-src") or img.get("lazy-src") or img.get("src", "")
            if src and ("cloudinary" in src or "annabasson" in src or src.startswith("http")):
                # Upgrade to larger size if Cloudinary URL
                if "cloudinary" in src:
                    src = re.sub(r"/w_\d+,h_\d+", "/w_800,h_600", src)
                    src = re.sub(r"/c_fill,w_\d+,h_\d+", "/c_fill,w_800,h_600", src)
                if src not in photo_urls:
                    photo_urls.append(src)

        return {
            "source": SourceSlug.ANNA_BASSON,
            "source_listing_id": f"ab_{listing_id}",
            "source_url": href or f"{self.BASE_URL}/properties/details/{listing_id}",
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": beds,
            "bathrooms": baths,
            "floor_size_m2": floor_size,
            "erf_size_m2": None,
            "parking": None,
            "latitude": None,
            "longitude": None,
            "raw_address": suburb,
            "suburb": suburb,
            "title": title,
            "description": "",
            "photo_urls": photo_urls,
            "agency": {
                "source_agent_id": "anna_basson_main",
                "name": "Anna Basson Eiendomme",
                "agency_name": "Anna Basson Eiendomme",
                "phone": "+27 21 883 3464",
                "photo_url": "",
                "agency_logo_url": f"{self.BASE_URL}/images/logo.png",
                "profile_url": self.BASE_URL,
                "agent_type": "agency",
            },
            "raw_data": {"listing_id": listing_id, "href": href},
        }

"""
Engel & Völkers South Africa scraper.
Website: https://www.engelvoelkers.com/en-za/
Strategy: JSON search API — E&V exposes a REST/GraphQL search endpoint.
The site is React-rendered but proxies to an underlying search service.
API endpoint discovered from network inspection: /api/search/properties
Falls back to HTML parsing if API is unavailable.
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

AREA_MAP: dict[str, list[dict]] = {
    AreaSlug.STELLENBOSCH: [
        {"location": "Stellenbosch", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.FRANSCHHOEK: [
        {"location": "Franschhoek", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.PAARL: [
        {"location": "Paarl", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.SOMERSET_WEST: [
        {"location": "Somerset West", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.STRAND: [
        {"location": "Strand", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.CITY_BOWL: [
        {"location": "Cape Town", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.ATLANTIC_SEABOARD: [
        {"location": "Camps Bay", "country": "ZA", "region": "Western Cape"},
        {"location": "Clifton", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.SOUTHERN_SUBURBS: [
        {"location": "Constantia", "country": "ZA", "region": "Western Cape"},
        {"location": "Claremont", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.HOUT_BAY: [
        {"location": "Hout Bay", "country": "ZA", "region": "Western Cape"},
    ],
    AreaSlug.HELDERBERG: [
        {"location": "Gordon's Bay", "country": "ZA", "region": "Western Cape"},
    ],
}

PROPERTY_TYPE_MAP = {
    "apartment":  PropertyType.APARTMENT,
    "flat":       PropertyType.APARTMENT,
    "house":      PropertyType.HOUSE,
    "townhouse":  PropertyType.TOWNHOUSE,
    "villa":      PropertyType.HOUSE,
    "farm":       PropertyType.FARM,
    "wine estate": PropertyType.FARM,
    "plot":       PropertyType.PLOT,
    "land":       PropertyType.PLOT,
    "commercial": PropertyType.COMMERCIAL,
}


def _detect_property_type(text: str) -> str:
    text_lower = text.lower()
    for keyword, ptype in PROPERTY_TYPE_MAP.items():
        if keyword in text_lower:
            return ptype
    return PropertyType.OTHER


class EngelVolkersScraper(BaseScraper):
    source = SourceSlug.ENGEL_VOLKERS
    BASE_URL = "https://www.engelvoelkers.com"
    # E&V search API endpoint — discovered from network inspection
    SEARCH_API = "https://www.engelvoelkers.com/en-za/search/"
    RATE_LIMIT_SECONDS = 3.0

    def __init__(self):
        super().__init__()
        # E&V requires more browser-like headers
        self.session.headers.update({
            "Accept": "application/json, text/html, */*",
            "Referer": "https://www.engelvoelkers.com/en-za/",
            "X-Requested-With": "XMLHttpRequest",
        })

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"locations": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        locations = AREA_MAP.get(area, [])
        if not locations:
            return []

        listing_category = "let" if listing_type == ListingType.RENT else "buy"
        results = []

        for loc in locations:
            location_name = loc["location"]
            self.log(f"Scraping {location_name} ({listing_type})")

            # Strategy 1: Try JSON API
            api_results = self._scrape_via_api(location_name, listing_category, listing_type, area)
            if api_results:
                results.extend(api_results)
                continue

            # Strategy 2: HTML scraping fallback
            if BeautifulSoup is not None:
                html_results = self._scrape_via_html(location_name, listing_category, listing_type, area)
                results.extend(html_results)

        return results

    def _scrape_via_api(self, location: str, category: str, listing_type: str, area: str) -> list[dict]:
        """Try E&V's internal search API (JSON response)."""
        page = 0
        results = []
        while page * 18 <= self.MAX_PAGES * 18:
            try:
                resp = self.get(
                    self.SEARCH_API,
                    params={
                        "q": location,
                        "businessArea": category,
                        "pageIndex": page,
                        "pageSize": 18,
                        "country": "ZA",
                    },
                    headers={"Accept": "application/json"},
                )
                # E&V returns JSON with a specific structure
                if "application/json" not in resp.headers.get("Content-Type", ""):
                    return []  # Got HTML back — API not available
                data = resp.json()
                items = (
                    data.get("results")
                    or data.get("properties")
                    or data.get("listings")
                    or data.get("items")
                    or []
                )
                if not items:
                    break
                for item in items:
                    parsed = self._parse_api_item(item, listing_type, area)
                    if parsed:
                        results.append(parsed)
                total = data.get("totalCount") or data.get("total") or 0
                if (page + 1) * 18 >= total or len(items) < 18:
                    break
                page += 1
            except Exception as e:
                self.log(f"API error for {location}: {e}", "warning")
                break
        return results

    def _parse_api_item(self, item: dict, listing_type: str, area: str) -> dict | None:
        listing_id = str(
            item.get("id") or item.get("objectId") or item.get("propertyId") or ""
        )
        if not listing_id:
            return None

        price = self._safe_price(
            item.get("price") or item.get("askingPrice") or item.get("rentPerMonth") or 0
        )
        prop_type_raw = (item.get("propertyType") or item.get("subType") or item.get("type") or "").lower()
        prop_type = _detect_property_type(prop_type_raw)

        lat = self._safe_float(item.get("latitude") or item.get("lat"))
        lng = self._safe_float(item.get("longitude") or item.get("lng"))

        photos = item.get("images") or item.get("photos") or item.get("imageUrls") or []
        photo_urls = []
        for p in photos:
            url = p if isinstance(p, str) else (p.get("url") or p.get("src") or "")
            if url and url not in photo_urls:
                photo_urls.append(url)

        agent = item.get("agent") or item.get("contact") or {}
        agent_id = str(agent.get("id") or agent.get("agentId") or "")
        if not agent_id and agent:
            agent_id = hashlib.md5((agent.get("name") or "").encode()).hexdigest()[:16]
        agency = {
            "source_agent_id": f"ev_{agent_id or listing_id}",
            "name": agent.get("name") or agent.get("fullName") or "Engel & Völkers",
            "agency_name": "Engel & Völkers",
            "phone": agent.get("phone") or agent.get("mobile") or "",
            "photo_url": agent.get("photo") or agent.get("image") or "",
            "agency_logo_url": f"{self.BASE_URL}/typo3conf/ext/ev_core/Resources/Public/Images/ev-logo.svg",
            "profile_url": agent.get("profileUrl") or "",
            "agent_type": "agency",
        }

        detail_path = item.get("url") or item.get("detailUrl") or f"/en-za/property/{listing_id}"
        detail_url = detail_path if detail_path.startswith("http") else self.BASE_URL + detail_path

        return {
            "source": SourceSlug.ENGEL_VOLKERS,
            "source_listing_id": f"ev_{listing_id}",
            "source_url": detail_url,
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": self._safe_int(item.get("bedrooms") or item.get("bedroomCount")),
            "bathrooms": self._safe_float(item.get("bathrooms") or item.get("bathroomCount")),
            "floor_size_m2": self._safe_float(item.get("floorSize") or item.get("livingArea")),
            "erf_size_m2": self._safe_float(item.get("plotSize") or item.get("landArea")),
            "parking": self._safe_int(item.get("garages") or item.get("parkingSpaces")),
            "latitude": lat,
            "longitude": lng,
            "raw_address": str(item.get("address") or item.get("location") or ""),
            "suburb": str(item.get("suburb") or item.get("district") or ""),
            "title": str(item.get("title") or item.get("headline") or ""),
            "description": str(item.get("description") or item.get("teaser") or ""),
            "photo_urls": photo_urls,
            "agency": agency,
            "raw_data": item,
        }

    def _scrape_via_html(self, location: str, category: str, listing_type: str, area: str) -> list[dict]:
        """Fallback: scrape search results HTML page."""
        results = []
        page = 1
        while page <= self.MAX_PAGES:
            url = f"{self.BASE_URL}/en-za/{category}/{location.lower().replace(' ', '-')}-western-cape-south-africa/"
            try:
                resp = self.get(url, params={"pageIndex": page - 1})
                soup = BeautifulSoup(resp.text, "lxml")
                cards = (
                    soup.select("[class*='property-card']")
                    or soup.select("[class*='PropertyCard']")
                    or soup.select("[class*='listing-card']")
                    or soup.select("article[class*='property']")
                )
                if not cards:
                    break
                for card in cards:
                    parsed = self._parse_html_card(card, listing_type, area)
                    if parsed:
                        results.append(parsed)
                if len(cards) < 18:
                    break
                page += 1
            except Exception as e:
                self.log(f"HTML scrape error for {location}: {e}", "warning")
                break
        return results

    def _parse_html_card(self, card, listing_type: str, area: str) -> dict | None:
        link_el = card.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        id_match = re.search(r"/property/([^/?#]+)", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]
        if not listing_id:
            return None

        title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
        title = title_el.get_text(strip=True) if title_el else ""
        prop_type = _detect_property_type(title)

        price_el = card.select_one("[class*='price'], [class*='Price']")
        price = self._safe_price(price_el.get_text(strip=True) if price_el else "")

        suburb_el = card.select_one("[class*='location'], [class*='Location'], [class*='suburb']")
        suburb = suburb_el.get_text(strip=True) if suburb_el else ""

        photo_urls = []
        for img in card.select("img[src], img[data-src]"):
            src = img.get("data-src") or img.get("src", "")
            if src and src not in photo_urls and not src.endswith(".svg"):
                photo_urls.append(src)

        return {
            "source": SourceSlug.ENGEL_VOLKERS,
            "source_listing_id": f"ev_{listing_id}",
            "source_url": href,
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": None,
            "bathrooms": None,
            "floor_size_m2": None,
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
                "source_agent_id": "ev_main_za",
                "name": "Engel & Völkers",
                "agency_name": "Engel & Völkers",
                "phone": "",
                "photo_url": "",
                "agency_logo_url": f"{self.BASE_URL}/typo3conf/ext/ev_core/Resources/Public/Images/ev-logo.svg",
                "profile_url": f"{self.BASE_URL}/en-za/",
                "agent_type": "agency",
            },
            "raw_data": {"listing_id": listing_id, "href": href},
        }

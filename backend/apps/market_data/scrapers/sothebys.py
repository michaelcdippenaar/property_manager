"""
Sotheby's International Realty South Africa scraper.
Website: https://www.sothebysrealty.co.za
Strategy: Prop Data platform — JSON API at /api/properties or /wp-json/prop-data/v2/properties.
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

AREA_MAP: dict[str, list[str]] = {
    AreaSlug.STELLENBOSCH: ["Stellenbosch", "Stellenbosch Farms"],
    AreaSlug.FRANSCHHOEK:  ["Franschhoek"],
    AreaSlug.PAARL:        ["Paarl"],
    AreaSlug.SOMERSET_WEST: ["Somerset West"],
    AreaSlug.STRAND:       ["Strand"],
    AreaSlug.CITY_BOWL:    ["Cape Town", "Sea Point", "Green Point"],
    AreaSlug.ATLANTIC_SEABOARD: ["Camps Bay", "Clifton", "Bantry Bay"],
    AreaSlug.SOUTHERN_SUBURBS:  ["Constantia", "Bishopscourt", "Newlands"],
    AreaSlug.HOUT_BAY:     ["Hout Bay"],
    AreaSlug.HELDERBERG:   ["Gordon's Bay"],
}

PROPERTY_TYPE_MAP = {
    "apartment":  PropertyType.APARTMENT,
    "flat":       PropertyType.APARTMENT,
    "house":      PropertyType.HOUSE,
    "townhouse":  PropertyType.TOWNHOUSE,
    "villa":      PropertyType.HOUSE,
    "duplex":     PropertyType.DUPLEX,
    "simplex":    PropertyType.SIMPLEX,
    "farm":       PropertyType.FARM,
    "wine estate": PropertyType.FARM,
    "plot":       PropertyType.PLOT,
    "land":       PropertyType.PLOT,
    "commercial": PropertyType.COMMERCIAL,
}

# Prop Data API endpoints (tried in order)
PROP_DATA_API_PATHS = [
    "/wp-json/prop-data/v2/properties",
    "/api/properties",
    "/api/search",
    "/properties/search",
]


def _detect_property_type(text: str) -> str:
    text_lower = text.lower()
    for keyword, ptype in PROPERTY_TYPE_MAP.items():
        if keyword in text_lower:
            return ptype
    return PropertyType.OTHER


class SothebysRealtyScraper(BaseScraper):
    source = SourceSlug.SOTHEBYS
    BASE_URL = "https://www.sothebysrealty.co.za"
    RATE_LIMIT_SECONDS = 2.5
    _api_path: str | None = None  # cached once discovered

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def _discover_api_path(self) -> str | None:
        """Find which Prop Data API endpoint responds with JSON."""
        if self._api_path is not None:
            return self._api_path
        for path in PROP_DATA_API_PATHS:
            try:
                resp = self.get(
                    f"{self.BASE_URL}{path}",
                    params={"suburb": "Stellenbosch", "listingType": "ForSale", "pageSize": 1},
                    headers={"Accept": "application/json"},
                )
                ct = resp.headers.get("Content-Type", "")
                if "json" in ct:
                    data = resp.json()
                    if isinstance(data, (dict, list)):
                        self._api_path = path
                        self.log(f"Discovered API path: {path}")
                        return path
            except Exception:
                continue
        return None

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        suburbs = AREA_MAP.get(area, [])
        if not suburbs:
            return []

        listing_param = "ToRent" if listing_type == ListingType.RENT else "ForSale"
        results = []
        api_path = self._discover_api_path()

        for suburb in suburbs:
            self.log(f"Scraping {suburb} ({listing_type})")

            if api_path:
                suburb_results = self._scrape_via_api(api_path, suburb, listing_param, listing_type, area)
            else:
                suburb_results = self._scrape_via_html(suburb, listing_type, area)

            results.extend(suburb_results)

        return results

    def _scrape_via_api(self, api_path: str, suburb: str, listing_param: str, listing_type: str, area: str) -> list[dict]:
        results = []
        page = 1
        while page <= self.MAX_PAGES:
            try:
                resp = self.get(
                    f"{self.BASE_URL}{api_path}",
                    params={
                        "suburb": suburb,
                        "listingType": listing_param,
                        "province": "Western Cape",
                        "pageNumber": page,
                        "pageSize": 20,
                    },
                    headers={"Accept": "application/json"},
                )
                data = resp.json()
                listings = (
                    data.get("properties")
                    or data.get("listings")
                    or data.get("results")
                    or (data if isinstance(data, list) else [])
                )
                if not listings:
                    break
                for item in listings:
                    parsed = self._parse_listing(item, listing_type, area)
                    if parsed:
                        results.append(parsed)
                total = data.get("totalCount") or data.get("total") or 0
                if page * 20 >= (total or 0) or len(listings) < 20:
                    break
                page += 1
            except Exception as e:
                self.log(f"API error for {suburb} page {page}: {e}", "warning")
                break
        return results

    def _scrape_via_html(self, suburb: str, listing_type: str, area: str) -> list[dict]:
        if BeautifulSoup is None:
            return []
        results = []
        listing_param = "to-rent" if listing_type == ListingType.RENT else "for-sale"
        suburb_slug = suburb.lower().replace(" ", "-").replace("'", "")
        page = 1
        while page <= self.MAX_PAGES:
            url = f"{self.BASE_URL}/{listing_param}/{suburb_slug}/"
            try:
                resp = self.get(url, params={"page": page})
                soup = BeautifulSoup(resp.text, "lxml")
                cards = (
                    soup.select(".listing-card, .property-card, .prop-card")
                    or soup.select("[class*='listing'][class*='card']")
                    or soup.select("article.property")
                )
                if not cards:
                    break
                for card in cards:
                    parsed = self._parse_html_card(card, listing_type, area)
                    if parsed:
                        results.append(parsed)
                if len(cards) < 12:
                    break
                page += 1
            except Exception as e:
                self.log(f"HTML error for {suburb}: {e}", "warning")
                break
        return results

    def _parse_listing(self, item: dict, listing_type: str, area: str) -> dict | None:
        listing_id = str(
            item.get("id")
            or item.get("propertyId")
            or item.get("listingId")
            or item.get("referenceNumber")
            or item.get("webRef")
            or ""
        )
        if not listing_id:
            return None

        price = self._safe_price(
            item.get("price") or item.get("askingPrice") or item.get("rentalAmount") or 0
        )
        prop_type_raw = (item.get("propertyType") or item.get("type") or item.get("category") or "").lower()
        prop_type = _detect_property_type(prop_type_raw)

        lat = self._safe_float(item.get("latitude") or item.get("lat"))
        lng = self._safe_float(item.get("longitude") or item.get("lng") or item.get("lon"))

        photos = item.get("images") or item.get("photos") or item.get("imageUrls") or []
        photo_urls = []
        for p in photos:
            url = p if isinstance(p, str) else (p.get("url") or p.get("src") or p.get("imageUrl") or "")
            if url and url not in photo_urls:
                photo_urls.append(url)

        agent = item.get("agent") or item.get("agentDetails") or {}
        agent_id = str(agent.get("id") or agent.get("agentId") or "")
        if not agent_id and agent:
            agent_id = hashlib.md5((agent.get("name") or "").encode()).hexdigest()[:16]
        agency = {
            "source_agent_id": f"srsa_{agent_id or listing_id}",
            "name": agent.get("name") or agent.get("fullName") or "Sotheby's International Realty",
            "agency_name": "Sotheby's International Realty SA",
            "phone": agent.get("phone") or agent.get("cell") or "",
            "photo_url": agent.get("photo") or agent.get("image") or "",
            "agency_logo_url": f"{self.BASE_URL}/images/sothebys-logo.png",
            "profile_url": agent.get("profileUrl") or "",
            "agent_type": "agency",
        }

        detail_url = item.get("url") or item.get("detailUrl") or ""
        ref = item.get("webRef") or item.get("referenceNumber") or listing_id
        if not detail_url:
            detail_url = f"{self.BASE_URL}/property/{ref}"
        elif not detail_url.startswith("http"):
            detail_url = self.BASE_URL + detail_url

        return {
            "source": SourceSlug.SOTHEBYS,
            "source_listing_id": f"srsa_{listing_id}",
            "source_url": detail_url,
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": self._safe_int(item.get("bedrooms") or item.get("bedroomCount")),
            "bathrooms": self._safe_float(item.get("bathrooms") or item.get("bathroomCount")),
            "floor_size_m2": self._safe_float(item.get("floorSize") or item.get("grossFloorArea")),
            "erf_size_m2": self._safe_float(item.get("erfSize") or item.get("landSize")),
            "parking": self._safe_int(item.get("garages") or item.get("parkingSpaces")),
            "latitude": lat,
            "longitude": lng,
            "raw_address": str(item.get("address") or item.get("fullAddress") or ""),
            "suburb": str(item.get("suburb") or item.get("suburbName") or ""),
            "title": str(item.get("title") or item.get("headline") or ""),
            "description": str(item.get("description") or item.get("marketingDescription") or ""),
            "photo_urls": photo_urls,
            "agency": agency,
            "raw_data": item,
        }

    def _parse_html_card(self, card, listing_type: str, area: str) -> dict | None:
        link_el = card.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        id_match = re.search(r"/property/([^/?#]+)", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]
        if not listing_id:
            return None

        title_el = card.select_one("h2, h3, .listing-title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""
        prop_type = _detect_property_type(title)

        price_el = card.select_one(".price, .listing-price, [class*='price']")
        price = self._safe_price(price_el.get_text(strip=True) if price_el else "")

        suburb_el = card.select_one(".suburb, .location, [class*='location']")
        suburb = suburb_el.get_text(strip=True) if suburb_el else ""

        photo_urls = []
        for img in card.select("img[src], img[data-src]"):
            src = img.get("data-src") or img.get("src", "")
            if src and not src.endswith(".svg") and src not in photo_urls:
                photo_urls.append(src)

        return {
            "source": SourceSlug.SOTHEBYS,
            "source_listing_id": f"srsa_{listing_id}",
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
                "source_agent_id": "srsa_main",
                "name": "Sotheby's International Realty SA",
                "agency_name": "Sotheby's International Realty SA",
                "phone": "",
                "photo_url": "",
                "agency_logo_url": f"{self.BASE_URL}/images/sothebys-logo.png",
                "profile_url": self.BASE_URL,
                "agent_type": "agency",
            },
            "raw_data": {"listing_id": listing_id, "href": href},
        }

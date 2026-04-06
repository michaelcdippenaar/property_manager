"""
Seeff Properties scraper — strong Winelands and Western Cape presence.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

AREA_MAP: dict[str, list[str]] = {
    AreaSlug.CITY_BOWL: ["Cape Town City Centre", "Sea Point", "Green Point"],
    AreaSlug.ATLANTIC_SEABOARD: ["Camps Bay", "Clifton", "Bantry Bay"],
    AreaSlug.SOUTHERN_SUBURBS: ["Claremont", "Constantia", "Kenilworth", "Newlands", "Rondebosch"],
    AreaSlug.NORTHERN_SUBURBS_CPT: ["Bellville", "Durbanville", "Brackenfell"],
    AreaSlug.HELDERBERG: ["Somerset West", "Strand", "Gordon's Bay"],
    AreaSlug.FALSE_BAY: ["Fish Hoek", "Muizenberg"],
    AreaSlug.HOUT_BAY: ["Hout Bay"],
    AreaSlug.STELLENBOSCH: ["Stellenbosch"],
    AreaSlug.PAARL: ["Paarl", "Wellington"],
    AreaSlug.FRANSCHHOEK: ["Franschhoek"],
    AreaSlug.SOMERSET_WEST: ["Somerset West"],
    AreaSlug.STRAND: ["Strand"],
}

PROPERTY_TYPE_MAP = {
    "apartment": PropertyType.APARTMENT,
    "house": PropertyType.HOUSE,
    "townhouse": PropertyType.TOWNHOUSE,
    "simplex": PropertyType.SIMPLEX,
    "duplex": PropertyType.DUPLEX,
    "bachelor": PropertyType.BACHELOR,
    "studio": PropertyType.STUDIO,
    "farm": PropertyType.FARM,
    "plot": PropertyType.PLOT,
    "commercial": PropertyType.COMMERCIAL,
}


class SeeffScraper(BaseScraper):
    source = SourceSlug.SEEFF
    BASE_URL = "https://www.seeff.com"
    API_URL = "https://www.seeff.com/api/property/search"
    RATE_LIMIT_SECONDS = 2.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        suburbs = AREA_MAP.get(area, [])
        listing_category = "rental" if listing_type == ListingType.RENT else "sale"
        results = []

        for suburb in suburbs:
            self.log(f"Scraping {suburb} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                try:
                    resp = self.get(
                        self.API_URL,
                        params={
                            "suburb": suburb,
                            "province": "Western Cape",
                            "listingType": listing_category,
                            "page": page,
                            "limit": 20,
                        },
                        headers={"Accept": "application/json"},
                    )
                    data = resp.json()
                    listings = data.get("properties") or data.get("results") or data.get("listings") or []
                    if not listings:
                        break
                    for item in listings:
                        parsed = self._parse_listing(item, listing_type, area)
                        if parsed:
                            results.append(parsed)
                    if len(listings) < 20:
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {suburb} page {page}: {e}", "warning")
                    break

        return results

    def _parse_listing(self, item: dict, listing_type: str, area: str) -> dict | None:
        listing_id = str(item.get("id") or item.get("listingId") or item.get("propertyId") or "")
        if not listing_id:
            return None

        price = self._safe_price(item.get("price") or item.get("askingPrice") or item.get("monthlyRent"))
        prop_type_raw = (item.get("propertyType") or item.get("type") or "").lower()
        prop_type = PROPERTY_TYPE_MAP.get(prop_type_raw, PropertyType.OTHER)

        lat = self._safe_float(item.get("latitude") or item.get("lat"))
        lng = self._safe_float(item.get("longitude") or item.get("lng"))

        images = item.get("images") or item.get("photos") or []
        photo_urls = []
        for img in images:
            url = img if isinstance(img, str) else (img.get("url") or img.get("src") or "")
            if url:
                photo_urls.append(url)

        agent = item.get("agent") or {}
        agency = None
        if agent:
            agent_id = str(agent.get("id") or agent.get("agentId") or "")
            if not agent_id:
                agent_id = hashlib.md5((agent.get("name") or "").encode()).hexdigest()[:16]
            agency = {
                "source_agent_id": f"seeff_{agent_id}",
                "name": agent.get("name") or agent.get("fullName") or "",
                "agency_name": "Seeff Properties",
                "phone": agent.get("phone") or agent.get("cell") or "",
                "photo_url": agent.get("photo") or "",
                "agency_logo_url": f"{self.BASE_URL}/images/seeff-logo.png",
                "profile_url": f"{self.BASE_URL}/agent/{agent_id}",
                "agent_type": "agency",
            }

        detail_url = item.get("url") or item.get("detailUrl") or f"{self.BASE_URL}/property/{listing_id}"
        if detail_url and not detail_url.startswith("http"):
            detail_url = self.BASE_URL + detail_url

        return {
            "source": SourceSlug.SEEFF,
            "source_listing_id": listing_id,
            "source_url": detail_url,
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": self._safe_int(item.get("bedrooms")),
            "bathrooms": self._safe_float(item.get("bathrooms")),
            "floor_size_m2": self._safe_float(item.get("floorSize") or item.get("size")),
            "erf_size_m2": self._safe_float(item.get("erfSize") or item.get("landSize")),
            "parking": self._safe_int(item.get("garages") or item.get("parking")),
            "latitude": lat,
            "longitude": lng,
            "raw_address": str(item.get("address") or ""),
            "suburb": str(item.get("suburb") or ""),
            "title": str(item.get("title") or item.get("heading") or ""),
            "description": str(item.get("description") or ""),
            "photo_urls": photo_urls,
            "agency": agency,
            "raw_data": item,
        }

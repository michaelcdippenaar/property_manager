"""
PrivateProperty.co.za scraper — uses their internal JSON search API.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Map AreaSlug → list of suburb names used in PrivateProperty search
AREA_MAP: dict[str, list[str]] = {
    AreaSlug.CITY_BOWL: ["Cape Town City Centre", "De Waterkant", "Gardens", "Green Point", "Sea Point", "Woodstock"],
    AreaSlug.ATLANTIC_SEABOARD: ["Bantry Bay", "Camps Bay", "Clifton", "Fresnaye"],
    AreaSlug.SOUTHERN_SUBURBS: ["Claremont", "Constantia", "Kenilworth", "Newlands", "Rondebosch", "Wynberg", "Tokai"],
    AreaSlug.NORTHERN_SUBURBS_CPT: ["Bellville", "Brackenfell", "Durbanville", "Goodwood", "Kraaifontein", "Parow"],
    AreaSlug.HELDERBERG: ["Somerset West", "Strand", "Gordon's Bay"],
    AreaSlug.FALSE_BAY: ["Fish Hoek", "Kalk Bay", "Muizenberg", "Simon's Town"],
    AreaSlug.HOUT_BAY: ["Hout Bay"],
    AreaSlug.STELLENBOSCH: ["Stellenbosch"],
    AreaSlug.PAARL: ["Paarl", "Wellington"],
    AreaSlug.FRANSCHHOEK: ["Franschhoek"],
    AreaSlug.SOMERSET_WEST: ["Somerset West"],
    AreaSlug.STRAND: ["Strand"],
}

PROPERTY_TYPE_MAP = {
    "Apartment": PropertyType.APARTMENT,
    "House": PropertyType.HOUSE,
    "Townhouse": PropertyType.TOWNHOUSE,
    "Simplex": PropertyType.SIMPLEX,
    "Duplex": PropertyType.DUPLEX,
    "Bachelor Flat": PropertyType.BACHELOR,
    "Studio": PropertyType.STUDIO,
    "Commercial": PropertyType.COMMERCIAL,
    "Vacant Land": PropertyType.PLOT,
    "Farm": PropertyType.FARM,
}


class PrivatePropertyScraper(BaseScraper):
    source = SourceSlug.PRIVATE_PROPERTY
    BASE_URL = "https://www.privateproperty.co.za"
    API_URL = "https://www.privateproperty.co.za/api/search"
    RATE_LIMIT_SECONDS = 2.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        suburbs = AREA_MAP.get(area, [])
        category = "to-rent" if listing_type == ListingType.RENT else "for-sale"
        results = []

        for suburb in suburbs:
            self.log(f"Scraping {suburb} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                try:
                    resp = self.get(
                        self.API_URL,
                        params={
                            "searchTerm": suburb,
                            "category": category,
                            "page": page,
                            "pageSize": 20,
                        },
                        headers={"Accept": "application/json"},
                    )
                    data = resp.json()
                    listings = data.get("results") or data.get("listings") or data.get("properties") or []
                    if not listings:
                        break
                    for item in listings:
                        parsed = self._parse_listing(item, listing_type, area)
                        if parsed:
                            results.append(parsed)
                    total_pages = data.get("totalPages") or data.get("pages") or 1
                    if page >= total_pages or len(listings) < 20:
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {suburb} page {page}: {e}", "warning")
                    break

        return results

    def _parse_listing(self, item: dict, listing_type: str, area: str) -> dict | None:
        listing_id = str(item.get("id") or item.get("listingId") or item.get("referenceNumber") or "")
        if not listing_id:
            return None

        price_raw = item.get("price") or item.get("askingPrice") or item.get("rentalPrice") or 0
        price = self._safe_price(price_raw)

        prop_type_raw = item.get("propertyType") or item.get("type") or ""
        prop_type = PROPERTY_TYPE_MAP.get(prop_type_raw, PropertyType.OTHER)

        lat = self._safe_float(item.get("latitude") or item.get("lat"))
        lng = self._safe_float(item.get("longitude") or item.get("lng"))

        photos = item.get("images") or item.get("photos") or []
        photo_urls = [p if isinstance(p, str) else (p.get("url") or p.get("src") or "") for p in photos]
        photo_urls = [u for u in photo_urls if u]

        agent = item.get("agent") or {}
        agency = None
        if agent:
            agent_id = str(agent.get("id") or agent.get("agentId") or "")
            if not agent_id:
                agent_id = hashlib.md5((agent.get("name") or "").encode()).hexdigest()[:16]
            agency = {
                "source_agent_id": agent_id,
                "name": agent.get("name") or agent.get("fullName") or "",
                "agency_name": agent.get("agencyName") or agent.get("company") or "",
                "phone": agent.get("phone") or agent.get("cellPhone") or "",
                "photo_url": agent.get("photo") or agent.get("profilePicture") or "",
                "agency_logo_url": agent.get("agencyLogo") or "",
                "profile_url": f"{self.BASE_URL}/agent/{agent_id}" if agent_id else "",
                "agent_type": "agency",
            }

        detail_url = item.get("url") or item.get("detailUrl") or f"{self.BASE_URL}/property/{listing_id}"
        if detail_url and not detail_url.startswith("http"):
            detail_url = self.BASE_URL + detail_url

        return {
            "source": SourceSlug.PRIVATE_PROPERTY,
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
            "raw_address": str(item.get("address") or item.get("fullAddress") or ""),
            "suburb": str(item.get("suburb") or item.get("area") or ""),
            "title": str(item.get("title") or item.get("heading") or ""),
            "description": str(item.get("description") or ""),
            "photo_urls": photo_urls,
            "agency": agency,
            "raw_data": item,
        }

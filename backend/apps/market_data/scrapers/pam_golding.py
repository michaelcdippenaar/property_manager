"""
Pam Golding Properties scraper — dominant in Stellenbosch, wine estates, and Southern Suburbs.
Uses their search API (JSON responses).
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

logger = logging.getLogger(__name__)

AREA_MAP: dict[str, list[str]] = {
    AreaSlug.CITY_BOWL: ["Cape Town City Centre", "Sea Point", "Green Point", "De Waterkant"],
    AreaSlug.ATLANTIC_SEABOARD: ["Camps Bay", "Clifton", "Bantry Bay", "Fresnaye"],
    AreaSlug.SOUTHERN_SUBURBS: ["Constantia", "Bishopscourt", "Claremont", "Rondebosch", "Newlands"],
    AreaSlug.NORTHERN_SUBURBS_CPT: ["Durbanville", "Bellville"],
    AreaSlug.HELDERBERG: ["Somerset West", "Strand"],
    AreaSlug.FALSE_BAY: ["Fish Hoek", "Simon's Town", "Muizenberg"],
    AreaSlug.HOUT_BAY: ["Hout Bay"],
    AreaSlug.STELLENBOSCH: ["Stellenbosch", "Stellenbosch Farms", "Franschhoek"],
    AreaSlug.PAARL: ["Paarl", "Wellington"],
    AreaSlug.FRANSCHHOEK: ["Franschhoek"],
    AreaSlug.SOMERSET_WEST: ["Somerset West"],
    AreaSlug.STRAND: ["Strand"],
}

PROPERTY_TYPE_MAP = {
    "apartment": PropertyType.APARTMENT,
    "flat": PropertyType.APARTMENT,
    "house": PropertyType.HOUSE,
    "townhouse": PropertyType.TOWNHOUSE,
    "duplex": PropertyType.DUPLEX,
    "simplex": PropertyType.SIMPLEX,
    "bachelor": PropertyType.BACHELOR,
    "studio": PropertyType.STUDIO,
    "farm": PropertyType.FARM,
    "wine estate": PropertyType.FARM,
    "plot": PropertyType.PLOT,
    "vacant land": PropertyType.PLOT,
    "commercial": PropertyType.COMMERCIAL,
}


class PamGoldingScraper(BaseScraper):
    source = SourceSlug.PAM_GOLDING
    BASE_URL = "https://www.pamgolding.co.za"
    API_URL = "https://www.pamgolding.co.za/api/properties/search"
    RATE_LIMIT_SECONDS = 2.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        suburbs = AREA_MAP.get(area, [])
        transaction_type = "ToRent" if listing_type == ListingType.RENT else "ForSale"
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
                            "transactionType": transaction_type,
                            "province": "Western Cape",
                            "pageNumber": page,
                            "pageSize": 20,
                        },
                        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
                    )
                    data = resp.json()
                    listings = (
                        data.get("results")
                        or data.get("properties")
                        or data.get("listings")
                        or data.get("data", {}).get("results", [])
                        or []
                    )
                    if not listings:
                        break
                    for item in listings:
                        parsed = self._parse_listing(item, listing_type, area)
                        if parsed:
                            results.append(parsed)
                    total = data.get("totalCount") or data.get("total") or 0
                    if page * 20 >= total or len(listings) < 20:
                        break
                    page += 1
                except Exception as e:
                    self.log(f"Error scraping {suburb} page {page}: {e}", "warning")
                    break

        return results

    def _parse_listing(self, item: dict, listing_type: str, area: str) -> dict | None:
        listing_id = str(
            item.get("propertyId")
            or item.get("id")
            or item.get("listingId")
            or item.get("referenceNumber")
            or ""
        )
        if not listing_id:
            return None

        price_raw = item.get("price") or item.get("askingPrice") or item.get("rentalAmount") or 0
        price = self._safe_price(price_raw)

        prop_type_raw = (item.get("propertyType") or item.get("type") or "").lower()
        prop_type = PROPERTY_TYPE_MAP.get(prop_type_raw, PropertyType.OTHER)

        lat = self._safe_float(item.get("latitude") or item.get("lat"))
        lng = self._safe_float(item.get("longitude") or item.get("lng"))

        images = item.get("images") or item.get("photos") or item.get("imageUrls") or []
        photo_urls = []
        for img in images:
            if isinstance(img, str):
                photo_urls.append(img)
            elif isinstance(img, dict):
                url = img.get("url") or img.get("src") or img.get("mediumUrl") or ""
                if url:
                    photo_urls.append(url)

        agent = item.get("agent") or item.get("contactAgent") or {}
        agency = None
        if agent:
            agent_id = str(agent.get("agentId") or agent.get("id") or "")
            if not agent_id:
                agent_id = hashlib.md5((agent.get("name") or "").encode()).hexdigest()[:16]
            agency = {
                "source_agent_id": f"pam_{agent_id}",
                "name": agent.get("name") or agent.get("fullName") or "",
                "agency_name": "Pam Golding Properties",
                "phone": agent.get("phone") or agent.get("cellphone") or "",
                "photo_url": agent.get("photo") or agent.get("profileImage") or "",
                "agency_logo_url": f"{self.BASE_URL}/Content/images/logo.png",
                "profile_url": agent.get("profileUrl") or f"{self.BASE_URL}/agent/{agent_id}",
                "agent_type": "agency",
            }

        ref = item.get("webRef") or item.get("referenceNumber") or listing_id
        detail_url = item.get("url") or f"{self.BASE_URL}/property-detail/{ref}"
        if detail_url and not detail_url.startswith("http"):
            detail_url = self.BASE_URL + detail_url

        return {
            "source": SourceSlug.PAM_GOLDING,
            "source_listing_id": listing_id,
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

"""
Louw & Coetzee Properties scraper.
Website: https://lcproperties.co.za  (redirects from louwcoetzee.co.za)
Strategy: server-rendered HTML, BeautifulSoup. Smaller boutique agency,
focused on Somerset West, Strand, Helderberg area.
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

# Louw & Coetzee focuses on Helderberg / Somerset West area
AREA_MAP: dict[str, list[str]] = {
    AreaSlug.SOMERSET_WEST: ["somerset-west", "somerset-west-central"],
    AreaSlug.STRAND:        ["strand", "strand-central", "gordon's-bay"],
    AreaSlug.HELDERBERG:    ["gordons-bay", "somerset-west"],
    AreaSlug.STELLENBOSCH:  ["stellenbosch"],
    AreaSlug.FRANSCHHOEK:   ["franschhoek"],
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


class LouwCoetzeeScraper(BaseScraper):
    source = SourceSlug.LOUW_COETZEE
    BASE_URL = "https://lcproperties.co.za"
    RATE_LIMIT_SECONDS = 2.0

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"areas": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — cannot scrape Louw & Coetzee", "error")
            return []

        if area not in AREA_MAP:
            return []

        results = []
        listing_param = "rental" if listing_type == ListingType.RENT else "sale"
        area_slugs = AREA_MAP[area]

        # Strategy 1: area-filtered listing pages
        for area_slug in area_slugs:
            self.log(f"Scraping {area_slug} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                # Try multiple URL patterns common on SA property sites
                urls_to_try = [
                    f"{self.BASE_URL}/properties/{listing_param}/{area_slug}/",
                    f"{self.BASE_URL}/properties/?type={listing_param}&area={area_slug}&page={page}",
                    f"{self.BASE_URL}/{listing_param}/{area_slug}/",
                ]
                tried_any = False
                for url in urls_to_try if page == 1 else [urls_to_try[0]]:
                    try:
                        resp = self.get(url if page == 1 or "?" not in url else urls_to_try[1].replace(f"page=1", f"page={page}"))
                        soup = BeautifulSoup(resp.text, "lxml")
                        listings = self._parse_page(soup, listing_type, area)
                        if listings:
                            results.extend(listings)
                            tried_any = True
                            # Check for next page
                            next_link = soup.select_one("a.next, a[rel='next'], .pagination .next, [class*='next-page']")
                            if not next_link or len(listings) < 12:
                                page = self.MAX_PAGES  # break outer while
                            break
                    except Exception as e:
                        self.log(f"Error scraping {url}: {e}", "warning")
                        continue
                if not tried_any:
                    break
                page += 1

        # Strategy 2: if area-filtered returned nothing, try unfiltered all-properties page
        if not results:
            self.log(f"No results from area-filtered URLs, trying unfiltered ({listing_type})")
            try:
                url = f"{self.BASE_URL}/properties/{listing_param}/"
                resp = self.get(url)
                soup = BeautifulSoup(resp.text, "lxml")
                results = self._parse_page(soup, listing_type, area)
            except Exception as e:
                self.log(f"Unfiltered scrape failed: {e}", "warning")

        return results

    def _parse_page(self, soup, listing_type: str, area: str) -> list[dict[str, Any]]:
        # Try multiple card selector patterns
        cards = (
            soup.select(".property-card")
            or soup.select(".listing-card")
            or soup.select(".prop-card")
            or soup.select("article.property")
            or soup.select(".property-item")
            or soup.select("[class*='property'][class*='card']")
            or soup.select("[class*='listing'][class*='item']")
        )
        results = []
        for card in cards:
            parsed = self._parse_card(card, listing_type, area)
            if parsed:
                results.append(parsed)
        return results

    def _parse_card(self, card, listing_type: str, area: str) -> dict | None:
        link_el = card.select_one("a[href*='/properties/'], a[href*='/property/'], a[href]")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = self.BASE_URL + href

        # Extract ID from URL
        id_match = re.search(r"/propert(?:y|ies)/(?:details?/)?([^/?#]+)", href)
        listing_id = id_match.group(1) if id_match else hashlib.md5(href.encode()).hexdigest()[:16]
        if not listing_id or listing_id in ("rental", "sale", "for-sale", "to-rent"):
            return None

        # Title
        title_el = card.select_one("h2, h3, h4, .property-title, .card-title, [class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""
        prop_type = _detect_property_type(title)

        # Price
        price_el = card.select_one(".price, .property-price, [class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = self._safe_price(price_text)

        # Suburb
        loc_el = card.select_one(".location, .suburb, .address, [class*='location'], [class*='suburb']")
        suburb = loc_el.get_text(strip=True) if loc_el else ""

        # Bedrooms / bathrooms from icon+text pairs or dedicated elements
        beds = baths = parking = None
        for el in card.select("[class*='bed'], .bedrooms, .beds, [title*='bedroom']"):
            val = self._safe_int(re.sub(r"[^\d]", "", el.get_text(strip=True)))
            if val is not None:
                beds = val
                break
        for el in card.select("[class*='bath'], .bathrooms, .baths, [title*='bathroom']"):
            val = self._safe_float(re.sub(r"[^\d.]", "", el.get_text(strip=True)))
            if val is not None:
                baths = val
                break
        for el in card.select("[class*='park'], [class*='garage'], [title*='parking'], [title*='garage']"):
            val = self._safe_int(re.sub(r"[^\d]", "", el.get_text(strip=True)))
            if val is not None:
                parking = val
                break

        # Floor size
        floor_size = None
        for el in card.select("[class*='size'], [class*='floor'], [class*='m2'], [class*='sqm']"):
            text = el.get_text(strip=True).replace("m²", "").replace("sqm", "").strip()
            val = self._safe_float(text)
            if val is not None and 10 < val < 10000:
                floor_size = val
                break

        # Photos
        photo_urls = []
        for img in card.select("img[src], img[data-src], img[data-lazy]"):
            src = img.get("data-lazy") or img.get("data-src") or img.get("src", "")
            if src and src not in photo_urls and not src.endswith(".svg"):
                if not src.startswith("http"):
                    src = self.BASE_URL + src
                photo_urls.append(src)

        return {
            "source": SourceSlug.LOUW_COETZEE,
            "source_listing_id": f"lc_{listing_id}",
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
            "parking": parking,
            "latitude": None,
            "longitude": None,
            "raw_address": suburb,
            "suburb": suburb,
            "title": title,
            "description": "",
            "photo_urls": photo_urls,
            "agency": {
                "source_agent_id": "lc_main",
                "name": "Louw & Coetzee Properties",
                "agency_name": "Louw & Coetzee Properties",
                "phone": "+27 21 852 8240",
                "photo_url": "",
                "agency_logo_url": f"{self.BASE_URL}/images/logo.png",
                "profile_url": self.BASE_URL,
                "agent_type": "agency",
            },
            "raw_data": {"listing_id": listing_id, "href": href},
        }

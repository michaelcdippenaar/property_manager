"""
Property24 scraper — server-rendered HTML parsed with BeautifulSoup.
URL format: /{type}/{suburb-slug}/{city-slug}/western-cape/{location-id}/p{page}
Location IDs verified from live site (2025).
"""
from __future__ import annotations

import re
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from apps.market_data.models import AreaSlug, ListingType, PropertyType, SourceSlug
from .base import BaseScraper

# Map AreaSlug → list of (suburb_slug, city_slug, location_id)
# IDs sourced directly from Property24 listing URLs.
AREA_MAP: dict[str, list[tuple[str, str, str]]] = {
    AreaSlug.CITY_BOWL: [
        ("cape-town-city-centre", "cape-town", "9138"),
        ("gardens",               "cape-town", "9145"),
        ("green-point",           "cape-town", "11017"),
        ("three-anchor-bay",      "cape-town", "11022"),
        ("sea-point",             "cape-town", "11021"),
        ("foreshore",             "cape-town", "9143"),
        ("tamboerskloof",         "cape-town", "9163"),
        ("higgovale",             "cape-town", "9149"),
        ("woodstock",             "cape-town", "10164"),
    ],
    AreaSlug.ATLANTIC_SEABOARD: [
        ("bantry-bay",  "cape-town", "11013"),
        ("camps-bay",   "cape-town", "11014"),
        ("llandudno",   "cape-town", "9118"),
    ],
    AreaSlug.SOUTHERN_SUBURBS: [
        ("claremont",       "cape-town", "11741"),
        ("claremont-upper", "cape-town", "14225"),
        ("rondebosch",      "cape-town", "8682"),
        ("rosebank",        "cape-town", "8683"),
        ("plumstead",       "cape-town", "10094"),
        ("pinelands",       "cape-town", "8017"),
        ("grassy-park",     "cape-town", "10204"),
        ("zeekoevlei",      "cape-town", "9047"),
        ("pelican-park",    "cape-town", "9029"),
    ],
    AreaSlug.NORTHERN_SUBURBS_CPT: [
        ("tyger-valley",         "bellville",    "8227"),
        ("protea-valley",        "bellville",    "9473"),
        ("bellville-park",       "bellville",    "8216"),
        ("durbanville-central",  "durbanville",  "9520"),
        ("vierlanden",           "durbanville",  "9559"),
        ("pinehurst",            "durbanville",  "9572"),
        ("brackenfell-central",  "brackenfell",  "16670"),
        ("protea-heights",       "brackenfell",  "9602"),
        ("big-bay",              "blouberg",     "11579"),
        ("table-view",           "blouberg",     "11589"),
        ("parklands",            "blouberg",     "11588"),
        ("century-city",         "milnerton",    "8027"),
        ("montague-gardens",     "milnerton",    "8067"),
    ],
    AreaSlug.HELDERBERG: [
        ("gordons-bay-central",    "gordons-bay",    "7833"),
        ("harbour-island",         "gordons-bay",    "7827"),
        ("mountainside",           "gordons-bay",    "7829"),
        ("somerset-west-central",  "somerset-west",  "9019"),
        ("parel-vallei",           "somerset-west",  "7802"),
        ("heritage-park",          "somerset-west",  "7800"),
        ("firgrove",               "somerset-west",  "7803"),
    ],
    AreaSlug.FALSE_BAY: [
        # Cape Town area — scrape from city page for False Bay suburbs
        ("stonehurst-mountain-estate", "cape-town", "12840"),
        ("pelican-park",               "cape-town", "9029"),
    ],
    AreaSlug.HOUT_BAY: [
        ("hout-bay-central",   "hout-bay", "16694"),
        ("hout-bay-heights",   "hout-bay", "10119"),
        ("valley-area",        "hout-bay", "10129"),
        ("northshore",         "hout-bay", "10126"),
        ("the-meadows",        "hout-bay", "10133"),
    ],
    AreaSlug.STELLENBOSCH: [
        ("stellenbosch-central",  "stellenbosch", "8566"),
        ("stellenbosch-farms",    "stellenbosch", "8562"),
        ("paradyskloof",          "stellenbosch", "8540"),
        ("devon-park",            "stellenbosch", "8572"),
        ("raithby",               "stellenbosch", "7805"),
        ("techno-park",           "stellenbosch", "12985"),
        ("krigeville",            "stellenbosch", "8553"),
        # Additional suburbs discovered from live scrapes
        ("jonkershoek-ah",        "stellenbosch", "33223"),
        ("koelenhof-ah",          "stellenbosch", "16701"),
        ("nooitgedacht-village",  "stellenbosch", "14758"),
        ("sitari-country-estate", "stellenbosch", "16113"),
    ],
    AreaSlug.PAARL: [
        ("paarl-central", "paarl", "8631"),
        ("paarl-north",   "paarl", "8612"),
        ("paarl-south",   "paarl", "8623"),
    ],
    AreaSlug.FRANSCHHOEK: [
        ("franschhoek", "stellenbosch", "8570"),
    ],
    AreaSlug.SOMERSET_WEST: [
        ("somerset-west-central", "somerset-west", "9019"),
        ("parel-vallei",          "somerset-west", "7802"),
        ("la-concorde",           "somerset-west", "11630"),
    ],
    AreaSlug.STRAND: [
        ("strand-central", "strand", "7816"),
        ("strand-north",   "strand", "7819"),
        ("strand-south",   "strand", "10438"),
    ],
}

PROPERTY_TYPE_MAP = {
    "apartment": PropertyType.APARTMENT,
    "flat":      PropertyType.APARTMENT,
    "house":     PropertyType.HOUSE,
    "townhouse": PropertyType.TOWNHOUSE,
    "simplex":   PropertyType.SIMPLEX,
    "duplex":    PropertyType.DUPLEX,
    "studio":    PropertyType.STUDIO,
    "bachelor":  PropertyType.BACHELOR,
    "commercial":PropertyType.COMMERCIAL,
    "plot":      PropertyType.PLOT,
    "vacant land": PropertyType.PLOT,
    "farm":      PropertyType.FARM,
}


def _detect_property_type(text: str) -> str:
    text_lower = text.lower()
    for keyword, ptype in PROPERTY_TYPE_MAP.items():
        if keyword in text_lower:
            return ptype
    return PropertyType.OTHER


def _parse_image_url(raw: str) -> str:
    """Upgrade thumbnail URL to full-size."""
    if not raw:
        return ""
    # Replace Crop/Ensure/Thumbnail with a larger variant
    raw = re.sub(r'/(Crop\d+x\d+|Ensure\d+x\d+|Thumbnail)', "/Resize800x600", raw)
    return raw


class Property24Scraper(BaseScraper):
    source = SourceSlug.PROPERTY24
    BASE_URL = "https://www.property24.com"
    RATE_LIMIT_SECONDS = 2.5

    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        return {"suburbs": AREA_MAP.get(area, [])}

    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            self.log("beautifulsoup4 not installed — cannot scrape Property24", "error")
            return []

        path_segment = "to-rent" if listing_type == ListingType.RENT else "for-sale"
        suburbs = AREA_MAP.get(area, [])
        results = []

        for suburb_slug, city_slug, location_id in suburbs:
            self.log(f"Scraping {suburb_slug} ({listing_type})")
            page = 1
            while page <= self.MAX_PAGES:
                url = f"{self.BASE_URL}/{path_segment}/{suburb_slug}/{city_slug}/western-cape/{location_id}/p{page}"
                try:
                    resp = self.get(url)
                    soup = BeautifulSoup(resp.text, "lxml")
                    listings = self._parse_page(soup, listing_type, area, suburb_slug)
                    if not listings:
                        break
                    results.extend(listings)

                    # Check for next page
                    pager = soup.select_one(".p24_pager")
                    if not pager:
                        break
                    current_page_el = pager.select_one(".p24_pageSelected, .active")
                    next_el = pager.select_one("a[rel='next']") or pager.find("a", string=str(page + 1))
                    if not next_el or len(listings) < 20:
                        break
                    page += 1

                except Exception as e:
                    self.log(f"Error scraping {url}: {e}", "warning")
                    break

        return results

    def _parse_page(self, soup, listing_type: str, area: str, suburb_slug: str) -> list[dict[str, Any]]:
        # p24_tileContainer is the outer wrapper — avoids duplicate inner divs
        tiles = soup.select(".p24_tileContainer[data-listing-number]")
        results = []
        for tile in tiles:
            parsed = self._parse_tile(tile, listing_type, area, suburb_slug)
            if parsed:
                results.append(parsed)
        return results

    def _parse_tile(self, tile, listing_type: str, area: str, suburb_slug: str) -> dict | None:
        listing_id = tile.get("data-listing-number", "").strip()
        if not listing_id:
            return None

        # Link and title
        link_el = tile.select_one("a[href*='/western-cape/']")
        href = link_el.get("href", "") if link_el else ""
        if href and not href.startswith("http"):
            href = self.BASE_URL + href
        # Strip query string from URL
        href = href.split("?")[0]

        # Title on the m-flex wrapper: "2 Bedroom Apartment / flat to rent in Stellenbosch Central"
        mflex = tile.select_one("div.m-flex[title]")
        title = mflex.get("title", "") if mflex else ""
        if not title:
            # Fallback: meta itemprop="name" inside tile
            name_meta = tile.select_one("meta[itemprop='name']")
            title = name_meta.get("content", "") if name_meta else ""
        prop_type = _detect_property_type(title)

        # Price — located in the price element; strip non-numeric text
        price_el = tile.select_one(".p24_price") or tile.select_one("[class*='price']")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = self._safe_price(price_text)

        # Location
        loc_el = tile.select_one(".p24_location")
        suburb_display = loc_el.get_text(strip=True) if loc_el else suburb_slug.replace("-", " ").title()

        # Feature details: bedrooms, bathrooms, parking (in order)
        feature_spans = tile.select(".p24_featureDetails:not(.p24_size)")
        size_span = tile.select_one(".p24_featureDetails.p24_size") or tile.select_one("[class*='size']")

        bedrooms = self._safe_int(feature_spans[0].get_text(strip=True)) if len(feature_spans) > 0 else None
        bathrooms = self._safe_float(feature_spans[1].get_text(strip=True)) if len(feature_spans) > 1 else None
        parking = self._safe_int(feature_spans[2].get_text(strip=True)) if len(feature_spans) > 2 else None

        floor_size = None
        if size_span:
            floor_size = self._safe_float(size_span.get_text(strip=True).replace("m²", "").strip())

        # Images — P24 lazy-loads; primary src is in lazy-src attr, fallback to src
        photo_urls = []
        for img in tile.select("img[lazy-src*='prop24.com'], img[src*='prop24.com']"):
            raw = img.get("lazy-src") or img.get("src", "")
            src = _parse_image_url(raw)
            if src and src not in photo_urls:
                photo_urls.append(src)

        # Agency branding — logo in .p24_branding span; name in itemprop="name" meta
        brand_el = tile.select_one(".p24_branding img")
        agency_logo_url = brand_el.get("src", "") if brand_el else ""
        agency_name_el = tile.select_one(".p24_branding [itemprop='name']")
        agency_display_name = agency_name_el.get("content", "") if agency_name_el else ""

        agency = None
        if agency_logo_url or agency_display_name:
            agency = {
                "source_agent_id": f"p24_brand_{listing_id}",
                "name": agency_display_name,
                "agency_name": agency_display_name,
                "phone": "",
                "photo_url": "",
                "agency_logo_url": agency_logo_url,
                "profile_url": "",
                "agent_type": "agency",
            }

        return {
            "source": SourceSlug.PROPERTY24,
            "source_listing_id": listing_id,
            "source_url": href or f"{self.BASE_URL}/property-details/{listing_id}",
            "listing_type": listing_type,
            "property_type": prop_type,
            "area": area,
            "asking_price": price if listing_type == ListingType.SALE else None,
            "rental_price": price if listing_type == ListingType.RENT else None,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floor_size_m2": floor_size,
            "erf_size_m2": None,
            "parking": parking,
            "latitude": None,
            "longitude": None,
            "raw_address": suburb_display,
            "suburb": suburb_display,
            "title": title,
            "description": "",
            "photo_urls": photo_urls,
            "agency": agency,
            "raw_data": {"listing_id": listing_id},
        }

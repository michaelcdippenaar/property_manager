"""
Municipal bylaw scraper — City of Cape Town and Stellenbosch Municipality.
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

logger = logging.getLogger(__name__)

BYLAW_SOURCES = [
    {
        "municipality": "city_of_cape_town",
        "name": "City of Cape Town",
        "url": "https://www.capetown.gov.za/en/City-Connect/Get/Municipal-services/Bylaws",
        "base_url": "https://www.capetown.gov.za",
    },
    {
        "municipality": "stellenbosch",
        "name": "Stellenbosch Municipality",
        "url": "https://www.stellenbosch.gov.za/documents/bylaws",
        "base_url": "https://www.stellenbosch.gov.za",
    },
    {
        "municipality": "drakenstein",
        "name": "Drakenstein Municipality",
        "url": "https://www.drakenstein.gov.za/Sectors/Legal-Services/By-Laws",
        "base_url": "https://www.drakenstein.gov.za",
    },
]

PROPERTY_BYLAW_KEYWORDS = [
    "property", "zoning", "building", "land use", "rates", "residential",
    "noise", "nuisance", "animal", "outdoor", "fence", "swimming pool",
    "rental", "occupancy", "subdivision", "consolidation",
]

BYLAW_CATEGORIES = {
    "zoning": ["zone", "land use", "subdivision", "consolidation"],
    "building": ["building", "construction", "structural"],
    "rates": ["rates", "tariff", "levy", "valuation"],
    "noise": ["noise", "nuisance", "disturbance"],
    "residential": ["residential", "occupancy", "habitability", "rental"],
    "environmental": ["environment", "tree", "water", "stormwater"],
    "animals": ["animal", "pet", "livestock"],
    "outdoor": ["fence", "wall", "pool", "outdoor", "signage"],
}


def _detect_category(title: str) -> str:
    title_lower = title.lower()
    for category, keywords in BYLAW_CATEGORIES.items():
        if any(kw in title_lower for kw in keywords):
            return category
    return "general"


def _is_property_relevant(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in PROPERTY_BYLAW_KEYWORDS)


def scrape_bylaws() -> list[dict[str, Any]]:
    if BeautifulSoup is None:
        logger.warning("beautifulsoup4 not installed — skipping bylaw scraping")
        return []

    import requests
    results = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; TremlyMarketBot/1.0; property research)"
    })

    for source_config in BYLAW_SOURCES:
        municipality = source_config["municipality"]
        url = source_config["url"]
        base_url = source_config["base_url"]

        logger.info("Scraping bylaws: %s", source_config["name"])
        try:
            resp = session.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, "lxml")

            # Look for PDF/document links to bylaws
            links = soup.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                title = link.get_text(strip=True)

                if not title or len(title) < 5:
                    continue

                # Include PDF bylaws and relevant pages
                is_pdf = href.lower().endswith(".pdf")
                is_relevant = _is_property_relevant(title)

                if not (is_pdf or is_relevant):
                    continue

                full_url = href if href.startswith("http") else f"{base_url}/{href.lstrip('/')}"
                bylaw_id = hashlib.md5(full_url.encode()).hexdigest()

                results.append({
                    "municipality": municipality,
                    "title": title,
                    "category": _detect_category(title),
                    "source_url": full_url,
                    "is_pdf": is_pdf,
                    "bylaw_id": bylaw_id,
                })

        except Exception as e:
            logger.warning("Error scraping bylaws from %s: %s", municipality, e)

    return results

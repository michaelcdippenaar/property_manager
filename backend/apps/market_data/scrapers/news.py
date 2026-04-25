"""
News scraper — RSS/Atom feeds for Cape Peninsula and Winelands property news.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

try:
    import feedparser
except ImportError:
    feedparser = None

from apps.market_data.models import AreaSlug

logger = logging.getLogger(__name__)

AREA_KEYWORDS: dict[str, list[str]] = {
    AreaSlug.CITY_BOWL:            ["cape town", "city bowl", "sea point", "green point", "woodstock", "de waterkant"],
    AreaSlug.ATLANTIC_SEABOARD:    ["atlantic seaboard", "camps bay", "clifton", "bantry"],
    AreaSlug.SOUTHERN_SUBURBS:     ["southern suburbs", "claremont", "constantia", "rondebosch", "newlands"],
    AreaSlug.NORTHERN_SUBURBS_CPT: ["durbanville", "bellville", "brackenfell", "kraaifontein"],
    AreaSlug.HELDERBERG:           ["helderberg", "somerset west", "strand", "gordon's bay"],
    AreaSlug.FALSE_BAY:            ["false bay", "fish hoek", "muizenberg", "kalk bay", "simon's town"],
    AreaSlug.HOUT_BAY:             ["hout bay"],
    AreaSlug.STELLENBOSCH:         ["stellenbosch"],
    AreaSlug.PAARL:                ["paarl", "wellington"],
    AreaSlug.FRANSCHHOEK:          ["franschhoek"],
    AreaSlug.SOMERSET_WEST:        ["somerset west"],
    AreaSlug.STRAND:               ["strand"],
}

PROPERTY_TOPICS = [
    "property", "real estate", "housing", "rental", "development", "zoning",
    "rezoning", "municipality", "rates", "levy", "sectional title", "freehold",
    "estate", "winelands", "wine farm", "sold", "listing", "infrastructure",
    "road", "school", "hospital", "shopping", "construction", "permit",
]

NEWS_FEEDS = [
    {
        "source": "news24_western_cape",
        "name": "News24 Western Cape",
        "url": "https://feeds.news24.com/articles/news24/WesternCape/rss",
    },
    {
        "source": "iol_property",
        "name": "IOL Property",
        "url": "https://www.iol.co.za/feed/property",
    },
    {
        "source": "groundup",
        "name": "GroundUp",
        "url": "https://www.groundup.org.za/article/rss.xml",
    },
    {
        "source": "eikestadnuus",
        "name": "Eikestadnuus",
        "url": "https://eikestadnuus.co.za/feed/",
    },
    {
        "source": "google_news_cpt_property",
        "name": "Google News: Cape Town Property",
        "url": "https://news.google.com/rss/search?q=cape+town+property+development+rental&hl=en-ZA&gl=ZA&ceid=ZA:en",
    },
    {
        "source": "google_news_stellenbosch",
        "name": "Google News: Stellenbosch Property",
        "url": "https://news.google.com/rss/search?q=stellenbosch+winelands+property&hl=en-ZA&gl=ZA&ceid=ZA:en",
    },
]


def _detect_areas(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for area, keywords in AREA_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(area)
    return found


def _is_property_related(text: str) -> bool:
    text_lower = text.lower()
    return any(topic in text_lower for topic in PROPERTY_TOPICS)


def scrape_news_feeds() -> list[dict[str, Any]]:
    if feedparser is None:
        logger.warning("feedparser not installed — skipping news scraping")
        return []

    results = []
    for feed_config in NEWS_FEEDS:
        source = feed_config["source"]
        url = feed_config["url"]
        logger.info("Scraping news feed: %s", source)

        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                link = getattr(entry, "link", "") or ""

                combined_text = f"{title} {summary}"
                if not _is_property_related(combined_text):
                    continue

                areas = _detect_areas(combined_text)

                # Parse published date
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Skipping news entry date parse [%s]: %s",
                            link or "<no-link>",
                            exc,
                            exc_info=True,
                        )

                article_id = hashlib.md5(link.encode()).hexdigest()

                results.append({
                    "source": source,
                    "source_article_id": article_id,
                    "title": title,
                    "url": link,
                    "published_at": published_at,
                    "content_summary": summary[:1000],
                    "areas_mentioned": areas,
                    "topics": _extract_topics(combined_text),
                    "raw_data": dict(entry),
                })

        except Exception as e:
            logger.warning("Error scraping %s: %s", source, e)

    return results


def _extract_topics(text: str) -> list[str]:
    text_lower = text.lower()
    topic_map = {
        "zoning": ["zon", "rezoning", "land use"],
        "development": ["develop", "construction", "build", "project"],
        "crime": ["crime", "theft", "robbery", "security"],
        "infrastructure": ["road", "water", "electricity", "sewage", "infrastructure"],
        "rates": ["rates", "municipality", "levy", "municipal"],
        "rental": ["rental", "rent", "tenant", "landlord", "lease"],
        "sale": ["sold", "sale", "purchase", "buy", "transfer"],
    }
    found = []
    for topic, keywords in topic_map.items():
        if any(kw in text_lower for kw in keywords):
            found.append(topic)
    return found

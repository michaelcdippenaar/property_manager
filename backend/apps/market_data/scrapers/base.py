"""
Base scraper class providing shared session management, rate limiting, and retry logic.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.market_data.models import AreaSlug, ListingType, SourceSlug

logger = logging.getLogger(__name__)

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)


def _build_session(retries: int = 3, backoff: float = 1.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BaseScraper(ABC):
    source: SourceSlug = NotImplemented
    RATE_LIMIT_SECONDS: float = 1.5
    MAX_PAGES: int = 50
    TIMEOUT: int = 20
    USER_AGENT: str = DESKTOP_UA

    def __init__(self):
        self.session = _build_session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-ZA,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        })
        self._last_request_time: float = 0.0

    def get(self, url: str, **kwargs) -> requests.Response:
        self._rate_limit()
        kwargs.setdefault("timeout", self.TIMEOUT)
        resp = self.session.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    def post(self, url: str, **kwargs) -> requests.Response:
        self._rate_limit()
        kwargs.setdefault("timeout", self.TIMEOUT)
        resp = self.session.post(url, **kwargs)
        resp.raise_for_status()
        return resp

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_SECONDS:
            time.sleep(self.RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()

    @abstractmethod
    def scrape(self, area: str, listing_type: str) -> list[dict[str, Any]]:
        """
        Return list of listing dicts. Each dict should contain at minimum:
          source_listing_id, source_url, listing_type, property_type,
          asking_price / rental_price, bedrooms, bathrooms, floor_size_m2,
          erf_size_m2, latitude, longitude, raw_address, suburb,
          title, description, listed_at, photo_urls (list), agency (dict or None)
        """
        raise NotImplementedError

    @abstractmethod
    def _area_to_search_params(self, area: str) -> dict[str, Any]:
        """Return source-specific search params (suburb names, IDs, bounding boxes)."""
        raise NotImplementedError

    def _safe_float(self, val) -> float | None:
        try:
            return float(str(val).replace(",", "").replace(" ", "").replace("m²", "").strip())
        except (TypeError, ValueError):
            return None

    def _safe_int(self, val) -> int | None:
        f = self._safe_float(val)
        return int(f) if f is not None else None

    def _safe_price(self, val) -> float | None:
        if val is None:
            return None
        clean = str(val).replace("R", "").replace(",", "").replace(" ", "").replace("\xa0", "").strip()
        try:
            return float(clean)
        except ValueError:
            return None

    def log(self, msg: str, level: str = "info"):
        getattr(logger, level)("[%s] %s", self.source, msg)

"""
Google Maps API service — Street View Static, Places Nearby Search, Distance Matrix.
Requires GOOGLE_MAPS_API_KEY in environment.
"""
from __future__ import annotations

import io
import logging
import math
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

PLACE_TYPE_GROUPS = [
    ("school",      ["school", "university", "primary_school", "secondary_school"]),
    ("supermarket", ["supermarket", "grocery_or_supermarket", "shopping_mall"]),
    ("hospital",    ["hospital", "doctor", "pharmacy", "medical_center"]),
    ("gym",         ["gym", "park", "stadium"]),
    ("transit",     ["transit_station", "bus_station", "train_station", "subway_station"]),
    ("restaurant",  ["restaurant", "cafe", "food"]),
    ("winery",      ["tourist_attraction", "lodging", "point_of_interest"]),
]

SEARCH_RADIUS_M = 2000  # 2 km radius for nearby places


def _get_api_key() -> str | None:
    return getattr(settings, "GOOGLE_MAPS_API_KEY", None)


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Calculate straight-line distance in metres between two lat/lng pairs."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


class GoogleMapsService:
    STREET_VIEW_URL = "https://maps.googleapis.com/maps/api/streetview"
    STREET_VIEW_META_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
    PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    DISTANCE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

    def __init__(self):
        self.api_key = _get_api_key()
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def fetch_street_view(
        self,
        lat: float,
        lng: float,
        size: str = "640x480",
        heading: float = 0.0,
        pitch: float = 0.0,
        fov: int = 90,
    ) -> tuple[bytes | None, str]:
        """
        Returns (jpeg_bytes, api_status).
        api_status is one of: OK, ZERO_RESULTS, NOT_FOUND, ERROR.
        """
        if not self.api_key:
            return None, "ERROR"

        # Check metadata first (free call) to avoid billing for zero-result images
        meta_resp = self.session.get(
            self.STREET_VIEW_META_URL,
            params={
                "location": f"{lat},{lng}",
                "key": self.api_key,
            },
            timeout=15,
        )
        meta = meta_resp.json()
        status = meta.get("status", "ERROR")
        if status != "OK":
            return None, status

        # Fetch the actual image
        resp = self.session.get(
            self.STREET_VIEW_URL,
            params={
                "size": size,
                "location": f"{lat},{lng}",
                "heading": heading,
                "pitch": pitch,
                "fov": fov,
                "key": self.api_key,
            },
            timeout=20,
        )
        if resp.status_code == 200 and resp.content:
            return resp.content, "OK"
        return None, "ERROR"

    def fetch_nearby_places(
        self,
        lat: float,
        lng: float,
        place_types: list[str],
        category_label: str,
        radius_m: int = SEARCH_RADIUS_M,
    ) -> list[dict[str, Any]]:
        """
        Fetch up to 60 places (3 pages × 20) for the given types.
        Returns list of dicts ready for ListingNearbyPlace creation.
        """
        if not self.api_key:
            return []

        all_results = []
        next_page_token = None

        for page_num in range(3):
            params: dict[str, Any] = {
                "location": f"{lat},{lng}",
                "radius": radius_m,
                "type": "|".join(place_types),
                "key": self.api_key,
            }
            if next_page_token:
                params = {"pagetoken": next_page_token, "key": self.api_key}
                time.sleep(2)  # Google requires a brief wait before using next_page_token

            try:
                resp = self.session.get(self.PLACES_URL, params=params, timeout=15)
                data = resp.json()
                status = data.get("status")
                if status not in ("OK", "ZERO_RESULTS"):
                    logger.warning("Places API error: %s for types %s", status, place_types)
                    break

                for place in data.get("results", []):
                    place_lat = place.get("geometry", {}).get("location", {}).get("lat")
                    place_lng = place.get("geometry", {}).get("location", {}).get("lng")
                    distance = None
                    if place_lat and place_lng:
                        distance = _haversine_distance(lat, lng, place_lat, place_lng)

                    all_results.append({
                        "place_id": place.get("place_id", ""),
                        "name": place.get("name", ""),
                        "category": category_label,
                        "place_type": ", ".join(place.get("types", [])),
                        "distance_m": distance,
                        "latitude": place_lat,
                        "longitude": place_lng,
                        "rating": place.get("rating"),
                        "drive_minutes": None,
                        "walk_minutes": None,
                    })

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

            except Exception as e:
                logger.warning("Error fetching places: %s", e)
                break

        return all_results

    def fetch_travel_times(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> dict[str, int | None]:
        """Returns {"drive_minutes": X, "walk_minutes": Y} or None values on error."""
        if not self.api_key:
            return {"drive_minutes": None, "walk_minutes": None}

        result = {"drive_minutes": None, "walk_minutes": None}
        origin = f"{origin_lat},{origin_lng}"
        destination = f"{dest_lat},{dest_lng}"

        for mode, key in [("driving", "drive_minutes"), ("walking", "walk_minutes")]:
            try:
                resp = self.session.get(
                    self.DISTANCE_URL,
                    params={
                        "origins": origin,
                        "destinations": destination,
                        "mode": mode,
                        "key": self.api_key,
                    },
                    timeout=15,
                )
                data = resp.json()
                rows = data.get("rows", [])
                if rows:
                    elements = rows[0].get("elements", [])
                    if elements and elements[0].get("status") == "OK":
                        seconds = elements[0].get("duration", {}).get("value", 0)
                        result[key] = max(1, round(seconds / 60))
            except Exception as e:
                logger.warning("Error fetching %s travel time: %s", mode, e)

        return result

    def enrich_listing_places(self, lat: float, lng: float) -> list[dict[str, Any]]:
        """
        Fetch all place categories for a listing's coordinates.
        Returns combined list of nearby place dicts.
        """
        all_places: list[dict] = []
        seen_place_ids: set[str] = set()

        for category_label, place_types in PLACE_TYPE_GROUPS:
            places = self.fetch_nearby_places(lat, lng, place_types, category_label)
            for place in places:
                pid = place.get("place_id", "")
                if pid and pid not in seen_place_ids:
                    seen_place_ids.add(pid)
                    all_places.append(place)

        # Fetch travel times for top 2 closest places per category
        for category_label, _ in PLACE_TYPE_GROUPS:
            category_places = sorted(
                [p for p in all_places if p["category"] == category_label and p.get("distance_m")],
                key=lambda p: p["distance_m"],
            )[:2]
            for place in category_places:
                if place.get("latitude") and place.get("longitude"):
                    times = self.fetch_travel_times(lat, lng, place["latitude"], place["longitude"])
                    place.update(times)

        return all_places

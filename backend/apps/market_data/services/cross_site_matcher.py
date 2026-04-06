"""
Cross-site duplicate detector for market listings.

Finds the same physical property listed on multiple portals (e.g. Property24
and Gumtree both listing 1 Bosch-en-Dal Karindal) using geospatial proximity,
price similarity, and property specs.

Usage:
    from apps.market_data.services.cross_site_matcher import find_cross_site_duplicates

    # Find + mark duplicates for Stellenbosch
    groups = find_cross_site_duplicates(area="stellenbosch", commit=True)
    print(f"{len(groups)} duplicate pairs found")

    # Dry run (no DB writes)
    groups = find_cross_site_duplicates(area="stellenbosch", commit=False)

    # All winelands
    groups = find_cross_site_duplicates(commit=True)

Algorithm:
    1. Load listings with coordinates for the target area(s)
    2. Grid-bucket into 0.001° cells (~110m) — avoids O(n²) comparison
    3. Compare pairs across different sources within each cell + 4 adjacent cells
    4. Score pairs: proximity +0.50, price +0.25, bedrooms +0.15, floor_size +0.10
    5. Pairs ≥ min_score (default 0.65) → duplicate candidates
    6. Union-Find merges transitively connected groups
    7. Within each group, oldest first_seen_at = canonical; others = duplicates
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict

logger = logging.getLogger(__name__)

PROXIMITY_THRESHOLD_M = 100   # listings within 100m are candidates
PRICE_SIMILARITY_PCT  = 0.10  # price must be within 10%
DEFAULT_MIN_SCORE     = 0.65


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in metres between two lat/lng pairs."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _cell(lat: float, lng: float) -> tuple[int, int]:
    """Round lat/lng to 0.001° grid (~110m cells)."""
    return round(lat, 3), round(lng, 3)


def _adjacent_cells(cell: tuple) -> list[tuple]:
    lat, lng = cell
    step = 0.001
    return [
        (lat + step, lng),
        (lat - step, lng),
        (lat, lng + step),
        (lat, lng - step),
    ]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_pair(a, b) -> float:
    """
    Returns a score 0.0–1.0 for how likely two listings describe the same property.
    Only called when a.source != b.source.
    """
    score = 0.0

    # Proximity (up to +0.50)
    if a.latitude and a.longitude and b.latitude and b.longitude:
        dist = _haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
        if dist < PROXIMITY_THRESHOLD_M:
            score += 0.50 * (1 - dist / PROXIMITY_THRESHOLD_M)

    # Price similarity (+0.25)
    price_a = float(a.rental_price or a.asking_price or 0)
    price_b = float(b.rental_price or b.asking_price or 0)
    if price_a and price_b:
        diff_pct = abs(price_a - price_b) / max(price_a, price_b)
        if diff_pct <= PRICE_SIMILARITY_PCT:
            score += 0.25

    # Bedrooms match (+0.15)
    if a.bedrooms is not None and b.bedrooms is not None:
        if a.bedrooms == b.bedrooms:
            score += 0.15
    else:
        score += 0.075  # unknown — partial credit

    # Floor size match within 5% (+0.10)
    if a.floor_size_m2 and b.floor_size_m2:
        fa, fb = float(a.floor_size_m2), float(b.floor_size_m2)
        if abs(fa - fb) / max(fa, fb) < 0.05:
            score += 0.10

    return round(score, 3)


# ---------------------------------------------------------------------------
# Union-Find for group merging
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self):
        self._parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self._parent.setdefault(x, x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int):
        self._parent.setdefault(x, x)
        self._parent.setdefault(y, y)
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx

    def groups(self) -> dict[int, list[int]]:
        result = defaultdict(list)
        for x in self._parent:
            result[self.find(x)].append(x)
        return {root: members for root, members in result.items() if len(members) > 1}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _mark_duplicates(groups: list[dict]):
    """Write canonical_listing, is_duplicate, duplicate_score back to DB."""
    from django.utils import timezone
    from apps.market_data.models import MarketListing

    uf = _UnionFind()
    pair_scores: dict[tuple[int, int], float] = {}

    for g in groups:
        a_pk = g["listing_a"].pk
        b_pk = g["listing_b"].pk
        uf.union(a_pk, b_pk)
        key = tuple(sorted([a_pk, b_pk]))
        pair_scores[key] = g["score"]

    # Build pk → listing map for everything involved
    all_pks = set(uf._parent.keys())
    listing_map: dict[int, object] = {
        l.pk: l
        for l in __import__("apps.market_data.models", fromlist=["MarketListing"]).MarketListing.objects.filter(pk__in=all_pks)
    }

    for root, members in uf.groups().items():
        # Canonical = oldest first_seen_at
        member_listings = [listing_map[pk] for pk in members if pk in listing_map]
        if not member_listings:
            continue
        canonical = min(member_listings, key=lambda l: l.first_seen_at or timezone.now())

        for listing in member_listings:
            if listing.pk == canonical.pk:
                # Ensure canonical is clean
                if listing.is_duplicate:
                    listing.is_duplicate = False
                    listing.canonical_listing = None
                    listing.save(update_fields=["is_duplicate", "canonical_listing"])
            else:
                pair_key = tuple(sorted([canonical.pk, listing.pk]))
                score = pair_scores.get(pair_key, 0.0)
                listing.is_duplicate = True
                listing.canonical_listing = canonical
                listing.duplicate_score = score
                listing.save(update_fields=["is_duplicate", "canonical_listing", "duplicate_score"])

    return len(uf.groups())


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def find_cross_site_duplicates(
    area: str | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
    commit: bool = True,
) -> list[dict]:
    """
    Find listings across different sources that describe the same property.

    Args:
        area: AreaSlug value (e.g. "stellenbosch") or None for all winelands.
        min_score: Minimum pair score (0.0–1.0) to consider a duplicate.
        commit: If True, writes is_duplicate / canonical_listing to DB.

    Returns:
        List of dicts: [{listing_a, listing_b, score}, ...]
    """
    from apps.market_data.models import MarketListing, WINELANDS_AREAS

    qs = MarketListing.objects.filter(latitude__isnull=False, is_duplicate=False)
    if area:
        qs = qs.filter(area=area)
    else:
        qs = qs.filter(area__in=[a.value for a in WINELANDS_AREAS])

    listings = list(qs)
    logger.info("cross_site_matcher: loaded %d listings", len(listings))

    # Build spatial grid
    buckets: dict[tuple, list] = defaultdict(list)
    for listing in listings:
        buckets[_cell(listing.latitude, listing.longitude)].append(listing)

    duplicate_pairs: list[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    for cell, cell_listings in buckets.items():
        # Gather candidates: this cell + 4 neighbours
        candidates = list(cell_listings)
        for adj in _adjacent_cells(cell):
            candidates.extend(buckets.get(adj, []))

        for i, a in enumerate(candidates):
            for b in candidates[i + 1:]:
                if a.source == b.source:
                    continue  # same portal — skip
                pair = tuple(sorted([a.pk, b.pk]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                score = _score_pair(a, b)
                if score >= min_score:
                    duplicate_pairs.append({"listing_a": a, "listing_b": b, "score": score})

    logger.info("cross_site_matcher: found %d duplicate pairs (commit=%s)", len(duplicate_pairs), commit)

    if commit and duplicate_pairs:
        groups_marked = _mark_duplicates(duplicate_pairs)
        logger.info("cross_site_matcher: marked %d duplicate groups", groups_marked)

    return duplicate_pairs

"""
Supplier matching algorithm for maintenance requests.
Ranks suppliers by proximity, skills, price history, owner preference, and rating.
"""
import math
from decimal import Decimal

from django.db.models import Avg

from .models import JobQuote, Supplier, SupplierProperty


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, map(float, [lat1, lon1, lat2, lon2]))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def rank_suppliers(maintenance_request, top_n=10):
    """
    Rank active suppliers for a maintenance request.
    Returns list of dicts: [{supplier, score, reasons}] sorted by score desc.
    """
    prop = maintenance_request.unit.property
    prop_lat = prop.latitude if hasattr(prop, "latitude") else None
    prop_lon = prop.longitude if hasattr(prop, "longitude") else None

    # Get all preferred/linked supplier IDs for this property
    preferred_ids = set(
        SupplierProperty.objects.filter(property=prop, is_preferred=True)
        .values_list("supplier_id", flat=True)
    )
    linked_ids = set(
        SupplierProperty.objects.filter(property=prop)
        .values_list("supplier_id", flat=True)
    )

    # Global average quote for price comparison
    global_avg = JobQuote.objects.aggregate(avg=Avg("amount"))["avg"] or Decimal("0")

    suppliers = Supplier.objects.filter(is_active=True).prefetch_related("trades")
    results = []

    for supplier in suppliers:
        score = 0.0
        reasons = {}

        # 1. Proximity (30%)
        if prop_lat and prop_lon and supplier.latitude and supplier.longitude:
            dist = haversine_km(prop_lat, prop_lon, supplier.latitude, supplier.longitude)
            radius = supplier.service_radius_km or 100
            if dist > radius:
                reasons["proximity"] = {"score": 0, "distance_km": round(dist, 1), "outside_radius": True}
            else:
                # Linear decay: 0km = 1.0, radius = 0.0
                prox_score = max(0, 1.0 - dist / radius)
                score += prox_score * 30
                reasons["proximity"] = {"score": round(prox_score * 30, 1), "distance_km": round(dist, 1)}
        else:
            # No geo data — neutral
            score += 15
            reasons["proximity"] = {"score": 15, "no_geo": True}

        # 2. Skills match (25%)
        supplier_trades = set(supplier.trade_list)
        # MaintenanceRequest doesn't have category yet, so match broadly
        # If we had a category field, we'd match against it
        if supplier_trades:
            # Having any trade is better than none
            skills_score = 25 if "general" in supplier_trades or len(supplier_trades) > 0 else 0
            score += skills_score
            reasons["skills"] = {"score": skills_score, "trades": list(supplier_trades)}
        else:
            reasons["skills"] = {"score": 0, "trades": []}

        # 3. Price history (15%)
        avg_quote = (
            JobQuote.objects.filter(quote_request__supplier=supplier)
            .aggregate(avg=Avg("amount"))["avg"]
        )
        if avg_quote and global_avg and global_avg > 0:
            # Lower than average = higher score
            price_ratio = float(avg_quote) / float(global_avg)
            price_score = max(0, min(15, 15 * (2 - price_ratio)))
            score += price_score
            reasons["price"] = {"score": round(price_score, 1), "avg_quote": float(avg_quote)}
        else:
            score += 7.5  # neutral
            reasons["price"] = {"score": 7.5, "no_history": True}

        # 4. Owner preference (20%)
        if supplier.id in preferred_ids:
            score += 20
            reasons["preference"] = {"score": 20, "preferred": True}
        elif supplier.id in linked_ids:
            score += 10
            reasons["preference"] = {"score": 10, "linked": True}
        else:
            reasons["preference"] = {"score": 0}

        # 5. Rating & reliability (10%)
        if supplier.rating:
            rating_score = (float(supplier.rating) / 5.0) * 10
            score += rating_score
            reasons["rating"] = {"score": round(rating_score, 1), "rating": float(supplier.rating)}
        else:
            score += 5  # neutral
            reasons["rating"] = {"score": 5, "no_rating": True}

        results.append({
            "supplier_id": supplier.id,
            "supplier_name": supplier.display_name,
            "supplier_phone": supplier.phone,
            "supplier_city": supplier.city,
            "trades": list(supplier_trades),
            "score": round(score, 1),
            "reasons": reasons,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

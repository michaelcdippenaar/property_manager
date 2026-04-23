"""
Owner dashboard aggregation service — RNT-QUAL-006.

Provides cache-backed stats and an activity feed for the owner dashboard.

Cache key pattern: ``owner_dashboard:<person_pk>``
TTL: 300 seconds (5 minutes) — short enough to feel fresh, long enough to
     avoid hammering the DB on every page load.

Cache invalidation is handled in ``dashboard_signals.py``.  Any signal that
writes data visible on the dashboard calls ``invalidate_owner_dashboard()``.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds


def _cache_key(person_pk: int) -> str:
    return f"owner_dashboard:{person_pk}"


def invalidate_owner_dashboard(person_pk: int) -> None:
    """Delete the cached dashboard payload for *person_pk*."""
    cache.delete(_cache_key(person_pk))
    logger.debug("owner_dashboard: cache invalidated for person %s", person_pk)


def get_dashboard_stats(person_pk: int) -> dict[str, Any]:
    """
    Return cached (or freshly computed) dashboard stats for the owner.

    Shape:
    {
        "total_properties": int,
        "total_units": int,
        "occupied_units": int,
        "occupancy_rate": int,           # 0–100
        "active_issues": int,
        "payment_performance": {
            "month": "YYYY-MM",
            "invoices_due": int,
            "invoices_paid": int,
            "total_due_zar": Decimal,
            "total_collected_zar": Decimal,
            "collection_rate": int,      # 0–100
        },
        "last_updated": "<ISO-8601 datetime>",
    }
    """
    key = _cache_key(person_pk)
    cached = cache.get(key)
    if cached is not None:
        return cached

    payload = _compute_dashboard_stats(person_pk)
    cache.set(key, payload, _CACHE_TTL)
    return payload


def _compute_dashboard_stats(person_pk: int) -> dict[str, Any]:
    from apps.properties.models import Property
    from apps.maintenance.models import MaintenanceRequest
    from apps.payments.models import RentInvoice, RentPayment

    props = Property.objects.filter(owner_id=person_pk).prefetch_related("units")
    total = props.count()
    total_units = 0
    occupied = 0
    prop_ids = []
    for p in props:
        prop_ids.append(p.pk)
        units = p.units.all()
        total_units += units.count()
        occupied += units.filter(status="occupied").count()

    issues = MaintenanceRequest.objects.filter(
        unit__property_id__in=prop_ids,
        status__in=["open", "in_progress"],
    ).count()

    # Payment performance: current calendar month
    today = date.today()
    month_str = today.strftime("%Y-%m")
    month_invoices = RentInvoice.objects.filter(
        lease__unit__property_id__in=prop_ids,
        period_start__year=today.year,
        period_start__month=today.month,
    )
    invoices_due = month_invoices.count()
    invoices_paid = month_invoices.filter(status__in=["paid", "overpaid"]).count()

    from django.db.models import Sum
    from decimal import Decimal

    total_due = month_invoices.aggregate(t=Sum("amount_due"))["t"] or Decimal("0.00")
    # Sum cleared payments for these invoices this month
    total_collected = (
        RentPayment.objects.filter(
            invoice__in=month_invoices,
            status="cleared",
        ).aggregate(t=Sum("amount"))["t"]
        or Decimal("0.00")
    )
    collection_rate = (
        round(float(total_collected) / float(total_due) * 100)
        if total_due
        else 0
    )

    return {
        "total_properties": total,
        "total_units": total_units,
        "occupied_units": occupied,
        "occupancy_rate": round((occupied / total_units * 100) if total_units else 0),
        "active_issues": issues,
        "payment_performance": {
            "month": month_str,
            "invoices_due": invoices_due,
            "invoices_paid": invoices_paid,
            "total_due_zar": str(total_due),
            "total_collected_zar": str(total_collected),
            "collection_rate": collection_rate,
        },
        "last_updated": timezone.now().isoformat(),
    }


def get_activity_feed(person_pk: int, limit: int = 20) -> list[dict[str, Any]]:
    """
    Return last *limit* events across the owner's portfolio.

    Each event dict:
    {
        "event_type": str,   # "rent_received" | "maintenance_opened" |
                             # "maintenance_closed" | "lease_signed" |
                             # "mandate_signed"
        "label": str,        # human-readable description
        "occurred_at": str,  # ISO-8601
        "meta": dict,        # extra context (unit, property, amount, etc.)
    }

    Events are sourced from Django ORM — no separate activity log table.
    We gather events from multiple models and sort them by timestamp, then
    return the most recent *limit* entries.
    """
    from apps.properties.models import Property, RentalMandate
    from apps.maintenance.models import MaintenanceRequest
    from apps.payments.models import RentPayment
    from apps.leases.models import Lease

    props = Property.objects.filter(owner_id=person_pk).values_list("pk", flat=True)
    prop_ids = list(props)
    if not prop_ids:
        return []

    events: list[dict[str, Any]] = []

    # --- Rent payments received (cleared, most recent first) ----------------
    payments = (
        RentPayment.objects
        .filter(invoice__lease__unit__property_id__in=prop_ids, status="cleared")
        .select_related("invoice__lease__unit__property", "invoice__lease__primary_tenant")
        .order_by("-payment_date")[:limit]
    )
    for p in payments:
        lease = p.invoice.lease
        unit = lease.unit
        tenant_name = (
            lease.primary_tenant.full_name if lease.primary_tenant else "Unknown tenant"
        )
        events.append({
            "event_type": "rent_received",
            "label": f"Rent received — {unit.property.name} u{unit.unit_number}",
            "occurred_at": _date_to_iso(p.payment_date),
            "meta": {
                "amount_zar": str(p.amount),
                "tenant_name": tenant_name,
                "property_name": unit.property.name,
                "unit_number": unit.unit_number,
            },
        })

    # --- Maintenance opened --------------------------------------------------
    opened = (
        MaintenanceRequest.objects
        .filter(unit__property_id__in=prop_ids)
        .select_related("unit__property")
        .order_by("-created_at")[:limit]
    )
    for r in opened:
        events.append({
            "event_type": "maintenance_opened",
            "label": f"Maintenance raised — {r.title[:60]}",
            "occurred_at": _dt_to_iso(r.created_at),
            "meta": {
                "request_id": r.pk,
                "priority": r.priority,
                "status": r.status,
                "property_name": r.unit.property.name,
                "unit_number": r.unit.unit_number,
            },
        })

    # --- Maintenance closed --------------------------------------------------
    closed = (
        MaintenanceRequest.objects
        .filter(
            unit__property_id__in=prop_ids,
            status__in=["resolved", "closed"],
            resolved_at__isnull=False,
        )
        .select_related("unit__property")
        .order_by("-resolved_at")[:limit]
    )
    for r in closed:
        events.append({
            "event_type": "maintenance_closed",
            "label": f"Maintenance resolved — {r.title[:60]}",
            "occurred_at": _dt_to_iso(r.resolved_at),
            "meta": {
                "request_id": r.pk,
                "property_name": r.unit.property.name,
                "unit_number": r.unit.unit_number,
            },
        })

    # --- Leases activated (signed) ------------------------------------------
    leases = (
        Lease.objects
        .filter(
            unit__property_id__in=prop_ids,
            status="active",
        )
        .select_related("unit__property", "primary_tenant")
        .order_by("-start_date")[:limit]
    )
    for ls in leases:
        tenant_name = ls.primary_tenant.full_name if ls.primary_tenant else "Unknown tenant"
        events.append({
            "event_type": "lease_signed",
            "label": f"Lease signed — {ls.unit.property.name} u{ls.unit.unit_number}",
            "occurred_at": _date_to_iso(ls.start_date),
            "meta": {
                "lease_id": ls.pk,
                "lease_number": ls.lease_number,
                "tenant_name": tenant_name,
                "property_name": ls.unit.property.name,
                "unit_number": ls.unit.unit_number,
                "monthly_rent": str(ls.monthly_rent),
            },
        })

    # --- Mandates activated (signed) ----------------------------------------
    mandates = (
        RentalMandate.objects
        .filter(
            property_id__in=prop_ids,
            status="active",
        )
        .select_related("property")
        .order_by("-start_date")[:limit]
    )
    for m in mandates:
        events.append({
            "event_type": "mandate_signed",
            "label": f"Mandate activated — {m.property.name}",
            "occurred_at": _date_to_iso(m.start_date),
            "meta": {
                "mandate_id": m.pk,
                "mandate_type": m.mandate_type,
                "property_name": m.property.name,
            },
        })

    # Sort all events by occurred_at descending and cap at limit
    events.sort(key=lambda e: e["occurred_at"], reverse=True)
    return events[:limit]


def _dt_to_iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt.isoformat()


def _date_to_iso(d: date | None) -> str:
    if d is None:
        return ""
    # Convert date → datetime at start of day in local tz for consistent sort
    return timezone.make_aware(
        datetime(d.year, d.month, d.day, 0, 0, 0)
    ).isoformat()

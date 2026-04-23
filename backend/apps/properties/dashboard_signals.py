"""
Owner dashboard cache invalidation signals — RNT-QUAL-006.

Listens for writes that affect data shown on the owner dashboard and
calls ``invalidate_owner_dashboard(person_pk)`` so the next request
recomputes fresh data.

Trigger points:
  - RentPayment saved      → rent received widget + payment performance
  - Lease status changed   → occupancy + lease_signed activity
  - MaintenanceRequest saved → active_issues count + activity feed
  - RentalMandate status → active  → mandate_signed activity

We resolve the owner (Person pk) for each write via the property/unit chain.
If the chain cannot be resolved we log and skip — never raise.

All receivers are registered via connect() in register() which is called from
PropertiesConfig.ready() to guarantee models are loaded before we reference them.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save

logger = logging.getLogger(__name__)


def _owner_pk_for_property(property_obj) -> int | None:
    """
    Return the Person.pk for the current owner of a property, or None.

    Tries two paths:
    1. PropertyOwnership table (canonical for multi-owner properties)
    2. Property.owner FK (legacy / simple setup)
    """
    try:
        from apps.properties.models import PropertyOwnership
        ownership = (
            PropertyOwnership.objects
            .filter(property=property_obj, is_current=True)
            .select_related("landlord__person")
            .first()
        )
        if ownership and ownership.landlord and ownership.landlord.person:
            return ownership.landlord.person.pk
    except Exception:
        logger.exception(
            "dashboard_signals: failed to resolve owner via PropertyOwnership for property %s",
            property_obj,
        )

    # Fallback: Property.owner FK (Person)
    try:
        if property_obj.owner_id:
            return property_obj.owner_id
    except Exception:
        pass

    return None


def _owner_pk_for_unit(unit_obj) -> int | None:
    try:
        return _owner_pk_for_property(unit_obj.property)
    except Exception:
        return None


def _bust(person_pk: int | None) -> None:
    if person_pk is None:
        return
    try:
        from apps.properties.dashboard_service import invalidate_owner_dashboard
        invalidate_owner_dashboard(person_pk)
    except Exception:
        logger.exception(
            "dashboard_signals: cache bust failed for person %s", person_pk
        )


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------

def _on_rent_payment_saved(sender, instance, created: bool, **kwargs):
    """Bust dashboard on any cleared payment write."""
    try:
        unit = instance.invoice.lease.unit
        _bust(_owner_pk_for_unit(unit))
    except Exception:
        logger.exception(
            "dashboard_signals: _on_rent_payment_saved error for payment %s", instance.pk
        )


def _on_lease_saved(sender, instance, created: bool, **kwargs):
    """Bust dashboard when a lease is created or its status changes."""
    try:
        _bust(_owner_pk_for_unit(instance.unit))
    except Exception:
        logger.exception(
            "dashboard_signals: _on_lease_saved error for lease %s", instance.pk
        )


def _on_maintenance_saved(sender, instance, created: bool, **kwargs):
    """Bust dashboard on maintenance create or status change."""
    try:
        _bust(_owner_pk_for_unit(instance.unit))
    except Exception:
        logger.exception(
            "dashboard_signals: _on_maintenance_saved error for request %s", instance.pk
        )


def _on_mandate_saved(sender, instance, created: bool, **kwargs):
    """Bust dashboard when a mandate becomes active."""
    try:
        _bust(_owner_pk_for_property(instance.property))
    except Exception:
        logger.exception(
            "dashboard_signals: _on_mandate_saved error for mandate %s", instance.pk
        )


def register():
    """
    Connect all dashboard invalidation signals.

    Must be called from PropertiesConfig.ready() after all models are loaded.
    Uses dispatch_uid to prevent duplicate registration in test runs.
    """
    from django.apps import apps

    RentPayment = apps.get_model("payments", "RentPayment")
    Lease = apps.get_model("leases", "Lease")
    MaintenanceRequest = apps.get_model("maintenance", "MaintenanceRequest")
    RentalMandate = apps.get_model("properties", "RentalMandate")

    post_save.connect(
        _on_rent_payment_saved,
        sender=RentPayment,
        dispatch_uid="owner_dashboard.rent_payment_saved",
    )
    post_save.connect(
        _on_lease_saved,
        sender=Lease,
        dispatch_uid="owner_dashboard.lease_saved",
    )
    post_save.connect(
        _on_maintenance_saved,
        sender=MaintenanceRequest,
        dispatch_uid="owner_dashboard.maintenance_saved",
    )
    post_save.connect(
        _on_mandate_saved,
        sender=RentalMandate,
        dispatch_uid="owner_dashboard.mandate_saved",
    )
    logger.debug("dashboard_signals: all invalidation signals registered")

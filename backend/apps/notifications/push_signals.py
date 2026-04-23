"""
Push notification dispatch signals.

Each receiver maps a key lifecycle event to a ``send_push_to_user`` call.
Failures are logged and swallowed — push must never break a database write.

Events covered
--------------
* Lease sent for signing  (status → pending + esigning submission created)
* Lease signed / active   (status → active)
* Mandate signed / active (RentalMandate.status → active)
* Rent received           (RentInvoice.status → paid or overpaid)
* Rent overdue            (dispatched by management command / Celery task via
                           ``dispatch_rent_overdue_push``)
* Maintenance logged      (MaintenanceRequest created)
* Maintenance updated     (MaintenanceRequest status changed)
* Chat message received   (MaintenanceActivity created with type note/status_change)

Deep-link data keys (consumed by agent-app router + tenant service worker):
  screen        — logical screen name in the receiving app
  <entity>_id   — primary key string for the target object

Agent screens:  lease_detail, mandate_detail, maintenance_detail, invoice_detail
Tenant screens: tenant_lease_detail, tenant_maintenance_detail, tenant_invoice_detail
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _push(user, title, body, *, data=None, category=None):
    """Dispatch push to *user* and swallow all errors."""
    if user is None:
        return
    try:
        from apps.notifications.services.push import send_push_to_user

        send_push_to_user(user, title, body, data=data, category=category)
    except Exception:
        logger.exception("push dispatch failed for user %s", getattr(user, "pk", "?"))


def _resolve_user(person_or_user):
    """Return a User from a Person (via linked_user) or a User directly."""
    if person_or_user is None:
        return None
    # Person model has a linked_user FK
    if hasattr(person_or_user, "linked_user"):
        return person_or_user.linked_user
    return person_or_user


# ─── Lease signals ────────────────────────────────────────────────────────────


@receiver(post_save, sender="leases.Lease")
def on_lease_status_change(sender, instance, created: bool, **kwargs):
    """
    Notify tenant + agent on:
      • status == pending  → lease sent for signing
      • status == active   → lease signed (all parties)
    """
    update_fields = kwargs.get("update_fields")
    status_changed = update_fields is None or "status" in (update_fields or [])
    if not status_changed:
        return

    tenant_user = _resolve_user(instance.primary_tenant)
    # Agent: resolve via unit → property → agent
    agent_user = None
    try:
        agent_user = instance.unit.property.agent
    except Exception:
        pass

    if instance.status == "pending":
        # Lease sent for signing
        _push(
            tenant_user,
            title="Lease ready to sign",
            body=f"Your lease for {instance.unit_label} has been sent — please review and sign.",
            data={"screen": "tenant_lease_detail", "lease_id": str(instance.pk)},
            category="lease",
        )
        _push(
            agent_user,
            title="Lease sent for signing",
            body=f"Lease for {instance.unit_label} ({instance.tenant_name}) awaits signatures.",
            data={"screen": "lease_detail", "lease_id": str(instance.pk)},
            category="lease",
        )

    elif instance.status == "active":
        # Lease fully signed
        _push(
            tenant_user,
            title="Lease signed",
            body=f"Your lease for {instance.unit_label} is now active. Welcome!",
            data={"screen": "tenant_lease_detail", "lease_id": str(instance.pk)},
            category="lease",
        )
        _push(
            agent_user,
            title="Lease signed",
            body=f"Lease for {instance.unit_label} ({instance.tenant_name}) is now active.",
            data={"screen": "lease_detail", "lease_id": str(instance.pk)},
            category="lease",
        )


# ─── Mandate signals ──────────────────────────────────────────────────────────


@receiver(post_save, sender="properties.RentalMandate")
def on_mandate_status_change(sender, instance, created: bool, **kwargs):
    """
    Notify agent when mandate becomes active (fully signed).
    """
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "status" not in update_fields:
        return

    if instance.status != "active":
        return

    # Agent: mandate → property → agent
    agent_user = None
    try:
        agent_user = instance.property.agent
    except Exception:
        pass

    property_name = ""
    try:
        property_name = instance.property.name
    except Exception:
        pass

    _push(
        agent_user,
        title="Mandate signed",
        body=f"The management mandate for {property_name} has been signed.",
        data={"screen": "mandate_detail", "mandate_id": str(instance.pk)},
        category="mandate",
    )


# ─── Payment signals ──────────────────────────────────────────────────────────


@receiver(post_save, sender="payments.RentInvoice")
def on_rent_invoice_paid(sender, instance, created: bool, **kwargs):
    """
    Notify agent when rent is received (invoice status → paid / overpaid).
    """
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "status" not in update_fields:
        return

    if instance.status not in ("paid", "overpaid"):
        return

    agent_user = None
    try:
        agent_user = instance.lease.unit.property.agent
    except Exception:
        pass

    unit_label = ""
    try:
        unit_label = instance.lease.unit_label
    except Exception:
        pass

    amount = ""
    try:
        from django.utils.formats import number_format

        amount = f"R {number_format(instance.amount_due, decimal_pos=2)}"
    except Exception:
        pass

    _push(
        agent_user,
        title="Rent received",
        body=f"Rent {amount} for {unit_label} has been received.",
        data={"screen": "invoice_detail", "invoice_id": str(instance.pk)},
        category="rent",
    )

    # Notify tenant too
    tenant_user = _resolve_user(instance.lease.primary_tenant) if instance.lease_id else None
    _push(
        tenant_user,
        title="Payment confirmed",
        body=f"Your rent payment of {amount} has been received. Thank you.",
        data={"screen": "tenant_invoice_detail", "invoice_id": str(instance.pk)},
        category="rent",
    )


def dispatch_rent_overdue_push(invoice) -> None:
    """
    Call this from a management command or Celery beat task when rent is overdue.

    Not a signal — rent overdue is time-based, not triggered by a model save.
    """
    agent_user = None
    try:
        agent_user = invoice.lease.unit.property.agent
    except Exception:
        pass

    tenant_user = _resolve_user(invoice.lease.primary_tenant) if invoice.lease_id else None

    unit_label = ""
    try:
        unit_label = invoice.lease.unit_label
    except Exception:
        pass

    _push(
        agent_user,
        title="Rent overdue",
        body=f"Rent for {unit_label} is overdue. Please follow up.",
        data={"screen": "invoice_detail", "invoice_id": str(invoice.pk)},
        category="rent",
    )
    _push(
        tenant_user,
        title="Rent overdue",
        body="Your rent is overdue. Please make payment as soon as possible.",
        data={"screen": "tenant_invoice_detail", "invoice_id": str(invoice.pk)},
        category="rent",
    )


# ─── Maintenance signals ──────────────────────────────────────────────────────


@receiver(post_save, sender="maintenance.MaintenanceRequest")
def on_maintenance_request_change(sender, instance, created: bool, **kwargs):
    """
    Notify tenant on new ticket logged; notify tenant on status update.
    Notify agent when a new ticket is created by tenant.
    """
    update_fields = kwargs.get("update_fields")

    tenant_user = _resolve_user(instance.tenant) if instance.tenant_id else None
    agent_user = None
    try:
        agent_user = instance.unit.property.agent
    except Exception:
        pass

    if created:
        # New maintenance request logged
        _push(
            agent_user,
            title="New maintenance request",
            body=f"{instance.title} — {instance.get_priority_display()} priority",
            data={
                "screen": "maintenance_detail",
                "maintenance_id": str(instance.pk),
            },
            category="maintenance",
        )
        # Also confirm to tenant that ticket was received
        _push(
            tenant_user,
            title="Maintenance request logged",
            body=f"Your request '{instance.title}' has been received and is being reviewed.",
            data={
                "screen": "tenant_maintenance_detail",
                "maintenance_id": str(instance.pk),
            },
            category="maintenance",
        )
    else:
        # Status update — only notify tenant
        if update_fields is None or "status" in (update_fields or []):
            status_label = dict(
                open="opened",
                in_progress="in progress",
                resolved="resolved",
                closed="closed",
            ).get(instance.status, instance.status)
            _push(
                tenant_user,
                title="Maintenance update",
                body=f"Your request '{instance.title}' is now {status_label}.",
                data={
                    "screen": "tenant_maintenance_detail",
                    "maintenance_id": str(instance.pk),
                },
                category="maintenance",
            )


@receiver(post_save, sender="maintenance.MaintenanceActivity")
def on_maintenance_activity(sender, instance, created: bool, **kwargs):
    """
    Notify the other party when a new chat message is posted on a ticket.

    If agent posts → notify tenant.
    If tenant posts → notify agent.
    """
    if not created:
        return

    # Only fire on note/status_change activity types (skip system/AI messages)
    if instance.activity_type not in ("note", "status_change"):
        return

    author = instance.created_by
    if author is None:
        return

    author_role = getattr(author, "role", "")

    request = instance.request
    tenant_user = _resolve_user(request.tenant) if request.tenant_id else None
    agent_user = None
    try:
        agent_user = request.unit.property.agent
    except Exception:
        pass

    if author_role in ("agent", "admin"):
        # Agent commented — notify tenant
        _push(
            tenant_user,
            title="Message on maintenance request",
            body=f"New update on '{request.title}': {instance.message[:100]}",
            data={
                "screen": "tenant_maintenance_detail",
                "maintenance_id": str(request.pk),
            },
            category="chat",
        )
    elif author_role == "tenant":
        # Tenant replied — notify agent
        _push(
            agent_user,
            title="Tenant replied",
            body=f"New message on '{request.title}': {instance.message[:100]}",
            data={
                "screen": "maintenance_detail",
                "maintenance_id": str(request.pk),
            },
            category="chat",
        )

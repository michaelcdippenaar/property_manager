"""
apps/audit/signals.py

Django signal handlers that write to the AuditEvent hash-chain for every
high-risk action on:

  - apps.leases.Lease
  - apps.properties.RentalMandate
  - apps.esigning.ESigningSubmission
  - apps.payments.RentPayment
  - apps.accounts.User (role field only)

Design notes
------------
* We ONLY READ from the connected apps; we never import or modify their
  models' field definitions.
* post_save is used for create/update.  pre_save is used to capture the
  before_snapshot for updates.
* We store a plain dict snapshot of the instance's fields — not the full
  model serialiser — to keep the audit app dependency-free.
* Chain linking: new events atomically claim the tail hash and write
  self_hash in one DB hit (select_for_update on the latest row prevents
  race conditions under concurrent writes).
"""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal registry: maps app_label.model_name -> action prefix string
# ---------------------------------------------------------------------------
_WATCHED_MODELS: dict[str, str] = {
    "leases.lease": "lease",
    "properties.rentalmandate": "mandate",
    "esigning.esigningsubmission": "signing",
    "payments.rentpayment": "payment",
    "accounts.user": "user",
}


# ---------------------------------------------------------------------------
# Agency resolution helpers
# ---------------------------------------------------------------------------

def _derive_agency_id(instance) -> int | None:
    """
    Best-effort resolver for the owning agency_id of an instance the audit
    signal observes.

    Tries common attribute paths used by the watched models:
      - ``instance.agency_id`` directly
      - ``instance.lease.agency_id``
      - ``instance.unit.property.agency_id``
      - ``instance.property.agency_id``

    Returns None if no chain resolves; the caller can then fall back to
    actor.agency_id or write the event with agency_id=NULL (operator-level
    events).
    """
    direct = getattr(instance, "agency_id", None)
    if direct:
        return direct

    lease = getattr(instance, "lease", None)
    if lease is not None:
        aid = getattr(lease, "agency_id", None)
        if aid:
            return aid

    unit = getattr(instance, "unit", None)
    if unit is not None:
        prop = getattr(unit, "property", None)
        if prop is not None:
            aid = getattr(prop, "agency_id", None)
            if aid:
                return aid

    prop = getattr(instance, "property", None)
    if prop is not None:
        aid = getattr(prop, "agency_id", None)
        if aid:
            return aid

    return None


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

def _model_to_dict(instance) -> dict:
    """
    Produce a plain-Python dict of an instance's concrete field values.

    We skip deferred fields and large binary columns (document_html) to keep
    snapshots lean.  All values are str()'d to ensure JSON serialisability.
    """
    SKIP_FIELDS = {"document_html", "password"}
    data: dict = {}
    for field in instance._meta.concrete_fields:
        if field.name in SKIP_FIELDS:
            continue
        try:
            val = getattr(instance, field.attname)
            # Coerce non-JSON-native types
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            elif hasattr(val, "__str__") and not isinstance(val, (bool, int, float, str, type(None))):
                val = str(val)
            data[field.attname] = val
        except Exception:
            data[field.attname] = None
    return data


# ---------------------------------------------------------------------------
# pre_save — capture before_snapshot for updates
# ---------------------------------------------------------------------------

# Thread-local storage would be cleaner, but Django's signal machinery runs
# synchronously so a module-level dict keyed by (model_label, pk) is safe.
_before_snapshots: dict[tuple, dict] = {}


@receiver(pre_save)
def _capture_before_snapshot(sender, instance, **kwargs):
    """Capture current DB state before any watched model is updated."""
    label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    if label not in _WATCHED_MODELS:
        return
    if not instance.pk:
        return  # new object — no prior state
    try:
        existing = sender.objects.get(pk=instance.pk)
        _before_snapshots[(label, instance.pk)] = _model_to_dict(existing)
    except sender.DoesNotExist:
        pass


# ---------------------------------------------------------------------------
# post_save — write AuditEvent
# ---------------------------------------------------------------------------

@receiver(post_save)
def _record_audit_event(sender, instance, created: bool, **kwargs):
    """Append an AuditEvent for every create/update on watched models."""
    label = f"{sender._meta.app_label}.{sender._meta.model_name}"
    if label not in _WATCHED_MODELS:
        return

    action_prefix = _WATCHED_MODELS[label]

    # Determine action code
    if created:
        action = f"{action_prefix}.created"
        before = None
    elif label == "accounts.user":
        # Only log role changes for User — not every profile edit
        snapshot_key = (label, instance.pk)
        before = _before_snapshots.pop(snapshot_key, None)
        if before is None:
            return
        if before.get("role") == instance.role:
            return  # role unchanged — skip
        action = "user.role_changed"
    else:
        snapshot_key = (label, instance.pk)
        before = _before_snapshots.pop(snapshot_key, None)
        action = f"{action_prefix}.updated"

    after = _model_to_dict(instance)
    _write_event(
        action=action,
        instance=instance,
        before=before,
        after=after,
    )


# ---------------------------------------------------------------------------
# Core writer
# ---------------------------------------------------------------------------

def _write_event(
    action: str,
    instance: Any,
    before: dict | None,
    after: dict | None,
    actor=None,
    ip_address: str | None = None,
    user_agent: str = "",
) -> None:
    """
    Append a new AuditEvent to the chain inside a serialisable transaction.

    The SELECT FOR UPDATE on the latest row serialises concurrent writers so
    the prev_hash is always correct.

    When ``actor``, ``ip_address``, or ``user_agent`` are not explicitly
    supplied (i.e. called from a signal handler that has no direct reference
    to the originating request), the values are pulled from the thread-local
    context stashed by ``AuditContextMiddleware``.  This ensures that events
    triggered indirectly by API calls still carry full attribution.
    """
    from .middleware import get_audit_context
    from .models import AuditEvent, compute_self_hash

    # Fall back to thread-local request context for unattributed signal writes.
    ctx = get_audit_context()
    if actor is None:
        actor = ctx.actor
    if ip_address is None:
        ip_address = ctx.ip
    if not user_agent:
        user_agent = ctx.user_agent or ""

    try:
        with transaction.atomic():
            # Lock the tail row to serialise concurrent event writes
            tail = (
                AuditEvent.objects.select_for_update()
                .order_by("-id")
                .first()
            )
            prev_hash = tail.self_hash if tail else ""

            ct = ContentType.objects.get_for_model(instance.__class__)

            actor_email = ""
            if actor is not None:
                actor_email = getattr(actor, "email", "") or ""
            elif hasattr(instance, "actor") and instance.actor is not None:
                actor_email = getattr(instance.actor, "email", "") or ""

            # Resolve owning agency for the audit row. Without this, every
            # signal-driven event would land with agency_id=NULL and the
            # AuditEventViewSet (which filters by agency_id) would hide the
            # event from the very agency_admin whose action created it.
            agency_id = _derive_agency_id(instance)
            if agency_id is None and actor is not None:
                agency_id = getattr(actor, "agency_id", None)
            if agency_id is None:
                logger.warning(
                    "AuditEvent missing agency_id for action=%s target=%s pk=%s",
                    action, type(instance).__name__, getattr(instance, "pk", None),
                )

            # Build the event (without self_hash first so we can compute canonical_payload)
            event = AuditEvent(
                agency_id=agency_id,
                actor=actor,
                actor_email=actor_email,
                action=action,
                content_type=ct,
                object_id=instance.pk,
                target_repr=str(instance)[:255],
                before_snapshot=before,
                after_snapshot=after,
                ip_address=ip_address,
                user_agent=user_agent,
                prev_hash=prev_hash,
                self_hash="",  # placeholder; computed below
            )

            # We need the PK to compute canonical_payload, so save first then update hash
            event.save()

            # Now compute the real hash (pk is set)
            event.self_hash = compute_self_hash(prev_hash, event.canonical_payload())
            event.save(update_fields=["self_hash"])

    except Exception:
        # Audit failures must NEVER break the main request/signal.
        logger.exception("AuditEvent write failed for action=%s target=%s pk=%s",
                         action, type(instance).__name__, getattr(instance, "pk", None))

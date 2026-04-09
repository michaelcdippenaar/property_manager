"""
Lease post_save broadcast signals.

Fires a websocket message to the ``lease_updates`` channel group whenever a
Lease row is created or updated so the admin Leases list can refresh in
real-time without polling.

Mirror of ``apps/maintenance/signals.py::broadcast_issue_update`` — same
channel layer + async_to_sync pattern, same failure semantics (log and
swallow, never raise).
"""
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.properties.models import Unit

from .models import Lease

logger = logging.getLogger(__name__)


def _resync_unit_status(unit: Unit | None) -> None:
    """
    Recompute Unit.status based on remaining ACTIVE leases only.

    Only 'active' (signed and in-progress) leases mark a unit as occupied.
    'pending' (future, not yet started) and 'expired' / 'terminated' do not.
    """
    if unit is None:
        return
    has_lease = Lease.objects.filter(unit=unit, status="active").exists()
    new_status = "occupied" if has_lease else "available"
    if unit.status != new_status:
        unit.status = new_status
        unit.save(update_fields=["status"])


@receiver(post_save, sender=Lease)
def sync_unit_status(sender, instance: Lease, **kwargs):
    """Keep Unit.status in sync with active/pending leases."""
    _resync_unit_status(instance.unit)


@receiver(post_delete, sender=Lease)
def sync_unit_status_on_delete(sender, instance: Lease, **kwargs):
    """Reset Unit.status when a lease is deleted (post_save isn't fired)."""
    # `instance.unit` is still cached on the in-memory object even after the
    # row is gone; fall back to a fresh lookup if the relation has been cleared.
    unit = instance.unit if instance.unit_id else None
    if unit is None and instance.unit_id:
        unit = Unit.objects.filter(pk=instance.unit_id).first()
    _resync_unit_status(unit)


@receiver(post_save, sender=Lease)
def broadcast_lease_update(sender, instance: Lease, created: bool, **kwargs):
    """Broadcast lease list changes to admin WebSocket clients."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            "lease_updates",
            {
                "type": "lease.update",
                "payload": {
                    "event": "lease_created" if created else "lease_updated",
                    "lease_id": instance.pk,
                    "status": instance.status,
                    "unit_id": instance.unit_id,
                    "primary_tenant_id": instance.primary_tenant_id,
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast lease update for #%s", instance.pk)

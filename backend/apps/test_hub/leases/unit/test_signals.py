"""
Unit tests for apps/leases/signals.py :: broadcast_lease_update.

broadcast_lease_update is a thin post_save handler that forwards
``Lease`` create/update events to the ``lease_updates`` channel group.
It must:
  - Fire on create with event="lease_created"
  - Fire on update with event="lease_updated"
  - Include lease_id, status, unit_id, and primary_tenant_id in payload
  - Never raise — log and swallow if the channel layer is unavailable
  - Short-circuit when get_channel_layer() returns None

The channel layer is fully mocked — no real Channels / Redis traffic.
"""
from unittest.mock import MagicMock, patch

import pytest

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestBroadcastLeaseUpdate:
    """Signal fires with the correct group and payload."""

    @patch("asgiref.sync.async_to_sync")
    @patch("channels.layers.get_channel_layer")
    def test_sends_lease_created_event_on_create(self, mock_get_layer, mock_async):
        from apps.leases.signals import broadcast_lease_update

        mock_get_layer.return_value = MagicMock()
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send

        instance = MagicMock()
        instance.pk = 101
        instance.status = "pending"
        instance.unit_id = 55
        instance.primary_tenant_id = 77

        broadcast_lease_update(sender=None, instance=instance, created=True)

        mock_async.assert_called_once()
        call_args = mock_group_send.call_args[0]
        assert call_args[0] == "lease_updates"

        message = call_args[1]
        assert message["type"] == "lease.update"
        payload = message["payload"]
        assert payload["event"] == "lease_created"
        assert payload["lease_id"] == 101
        assert payload["status"] == "pending"
        assert payload["unit_id"] == 55
        assert payload["primary_tenant_id"] == 77

    @patch("asgiref.sync.async_to_sync")
    @patch("channels.layers.get_channel_layer")
    def test_sends_lease_updated_event_on_update(self, mock_get_layer, mock_async):
        from apps.leases.signals import broadcast_lease_update

        mock_get_layer.return_value = MagicMock()
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send

        instance = MagicMock()
        instance.pk = 200
        instance.status = "active"
        instance.unit_id = 2
        instance.primary_tenant_id = 3

        broadcast_lease_update(sender=None, instance=instance, created=False)

        payload = mock_group_send.call_args[0][1]["payload"]
        assert payload["event"] == "lease_updated"
        assert payload["lease_id"] == 200
        assert payload["status"] == "active"

    @patch("asgiref.sync.async_to_sync")
    @patch("channels.layers.get_channel_layer")
    def test_handles_null_primary_tenant(self, mock_get_layer, mock_async):
        """Leases may have primary_tenant_id = None during import — must not crash."""
        from apps.leases.signals import broadcast_lease_update

        mock_get_layer.return_value = MagicMock()
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send

        instance = MagicMock()
        instance.pk = 300
        instance.status = "pending"
        instance.unit_id = 99
        instance.primary_tenant_id = None

        broadcast_lease_update(sender=None, instance=instance, created=True)

        payload = mock_group_send.call_args[0][1]["payload"]
        assert payload["primary_tenant_id"] is None

    # ── Defensive paths ──

    @patch("channels.layers.get_channel_layer")
    def test_no_channel_layer_is_noop(self, mock_get_layer):
        from apps.leases.signals import broadcast_lease_update

        mock_get_layer.return_value = None  # No channel layer configured

        instance = MagicMock()
        instance.pk = 1
        instance.status = "pending"
        instance.unit_id = 1
        instance.primary_tenant_id = 1

        # Should not raise
        broadcast_lease_update(sender=None, instance=instance, created=True)

    @patch("channels.layers.get_channel_layer", side_effect=Exception("channels error"))
    def test_channel_layer_exception_is_swallowed(self, mock_get_layer):
        from apps.leases.signals import broadcast_lease_update

        instance = MagicMock()
        instance.pk = 1
        instance.status = "pending"
        instance.unit_id = 1
        instance.primary_tenant_id = 1

        # Signal handler must catch all exceptions — any raise would bubble
        # out of post_save and blow up the view calling Lease.save()
        broadcast_lease_update(sender=None, instance=instance, created=True)


class BroadcastLeaseUpdateEndToEndTests(TremlyAPITestCase):
    """
    End-to-end: saving a real Lease row runs the signal and forwards a
    message to the channel layer.

    We patch ``async_to_sync`` inside the signal module so the ``group_send``
    call is captured synchronously — no real Channels traffic is needed.
    """

    def test_saving_lease_triggers_broadcast(self):
        from apps.leases.models import Lease

        unit = self.create_unit()

        with patch("asgiref.sync.async_to_sync") as mock_async:
            mock_group_send = MagicMock()
            mock_async.return_value = mock_group_send

            lease = Lease.objects.create(
                unit=unit,
                start_date="2026-01-01",
                end_date="2026-12-31",
                monthly_rent="5000.00",
                deposit="10000.00",
                status="pending",
            )

            self.assertTrue(mock_group_send.called)
            call_args = mock_group_send.call_args[0]
            self.assertEqual(call_args[0], "lease_updates")
            payload = call_args[1]["payload"]
            self.assertEqual(payload["event"], "lease_created")
            self.assertEqual(payload["status"], "pending")
            self.assertEqual(payload["unit_id"], unit.pk)
            self.assertEqual(payload["lease_id"], lease.pk)

    def test_updating_lease_emits_updated_event(self):
        from apps.leases.models import Lease

        unit = self.create_unit()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="pending",
        )

        with patch("asgiref.sync.async_to_sync") as mock_async:
            mock_group_send = MagicMock()
            mock_async.return_value = mock_group_send

            lease.status = "active"
            lease.save()

            self.assertTrue(mock_group_send.called)
            payload = mock_group_send.call_args[0][1]["payload"]
            self.assertEqual(payload["event"], "lease_updated")
            self.assertEqual(payload["status"], "active")
            self.assertEqual(payload["lease_id"], lease.pk)


class SyncUnitStatusTests(TremlyAPITestCase):
    """
    Unit.status occupancy rule:

    Only ``status='active'`` (signed and currently in-progress) leases
    occupy a unit.

      - 'pending'    → not yet started (and may also be unsigned) — does NOT occupy
      - 'expired'    → past its end date — does NOT occupy
      - 'terminated' → cancelled — does NOT occupy
      - 'active'     → signed AND in-progress — DOES occupy

    The signal recomputes Unit.status on every Lease post_save and post_delete.
    """

    def test_creating_active_lease_marks_unit_occupied(self):
        from apps.leases.models import Lease

        unit = self.create_unit()
        self.assertEqual(unit.status, "available")

        Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="active",
        )
        unit.refresh_from_db()
        self.assertEqual(unit.status, "occupied")

    def test_creating_pending_lease_leaves_unit_available(self):
        """Pending = future / unsigned. Does NOT occupy the unit."""
        from apps.leases.models import Lease

        unit = self.create_unit()
        Lease.objects.create(
            unit=unit,
            start_date="2026-06-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="pending",
        )
        unit.refresh_from_db()
        self.assertEqual(unit.status, "available")

    def test_deleting_only_active_lease_returns_unit_to_available(self):
        """Regression: prior to the post_delete signal the unit stayed 'occupied' forever."""
        from apps.leases.models import Lease

        unit = self.create_unit()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="active",
        )
        unit.refresh_from_db()
        self.assertEqual(unit.status, "occupied")

        lease.delete()

        unit.refresh_from_db()
        self.assertEqual(unit.status, "available")

    def test_terminating_lease_returns_unit_to_available(self):
        from apps.leases.models import Lease

        unit = self.create_unit()
        lease = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="active",
        )
        unit.refresh_from_db()
        self.assertEqual(unit.status, "occupied")

        lease.status = "terminated"
        lease.save()

        unit.refresh_from_db()
        self.assertEqual(unit.status, "available")

    def test_pending_alongside_active_does_not_block_release(self):
        """Active + future-pending: deleting the active makes the unit available
        because pending leases never count as occupying."""
        from apps.leases.models import Lease

        unit = self.create_unit()
        lease_active = Lease.objects.create(
            unit=unit,
            start_date="2026-01-01",
            end_date="2026-06-30",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="active",
        )
        Lease.objects.create(
            unit=unit,
            start_date="2026-07-01",
            end_date="2026-12-31",
            monthly_rent="5000.00",
            deposit="10000.00",
            status="pending",
        )
        unit.refresh_from_db()
        self.assertEqual(unit.status, "occupied")

        lease_active.delete()

        unit.refresh_from_db()
        self.assertEqual(unit.status, "available")

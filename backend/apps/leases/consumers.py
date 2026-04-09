"""
WebSocket consumers for the leases app.

LeaseUpdatesConsumer
--------------------
Broadcasts Lease row changes (created / updated) to all connected admin
clients so the /leases list refreshes in real-time, no polling required.

WebSocket URL: ws://host/ws/leases/updates/

Auth: requires an authenticated user (JWT via ?token=... query param handled
by apps.maintenance.middleware.JwtAuthMiddleware). Anonymous connections
are closed with code 4001 — matches the maintenance consumer contract.
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class LeaseUpdatesConsumer(AsyncWebsocketConsumer):
    """
    Push Lease create/update events to connected admin clients.

    Mirrors ``apps.maintenance.consumers.MaintenanceListConsumer`` — single
    process-wide channel group that every subscribed admin joins, with
    :func:`apps.leases.signals.broadcast_lease_update` dispatching events.
    """

    GROUP_NAME = "lease_updates"

    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def lease_update(self, event):
        """Forward a lease update event to the connected WebSocket client."""
        await self.send(text_data=json.dumps(event["payload"]))

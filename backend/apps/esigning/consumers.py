"""
WebSocket consumers for real-time e-signing status updates.

ESigningStatusConsumer
-----------------------
Clients connect to:  ws/esigning/<submission_id>/
They receive events when:
  - A signer views the document
  - A signer completes signing
  - A signer declines
  - The entire submission completes
  - The next signer is notified (sequential mode)

ESigningAgentNotificationsConsumer
------------------------------------
Clients connect to:  ws/esigning/notifications/
Agents receive global toast notifications for ALL signing events on
submissions they created / have access to — regardless of which panel is open.
Group name: signing_notifications_<user_pk>
"""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class ESigningStatusConsumer(AsyncWebsocketConsumer):
    """
    Group name: esigning_<submission_pk>
    Agents/admins who created the submission and tenants on the lease
    may subscribe.
    """

    async def connect(self):
        self.submission_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.group_name = f"esigning_{self.submission_pk}"
        user = self.scope.get("user")

        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        has_access = await self._check_access(user)
        if not has_access:
            await self.close(code=4003)
            return

        self.user = user
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send current state on connect
        state = await self._get_submission_state()
        if state:
            await self.send(text_data=json.dumps({"type": "status", **state}))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Clients can request a status refresh."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        if data.get("action") == "refresh":
            state = await self._get_submission_state()
            if state:
                await self.send(text_data=json.dumps({"type": "status", **state}))

    # ── Group-broadcast handlers ──────────────────────────────────────

    async def esigning_update(self, event):
        """Generic signing event broadcast."""
        await self.send(text_data=json.dumps(event["payload"]))

    # ── Helpers ───────────────────────────────────────────────────────

    @database_sync_to_async
    def _check_access(self, user):
        from apps.accounts.models import User
        from .models import ESigningSubmission

        try:
            sub = ESigningSubmission.objects.select_related("lease__unit__property").get(
                pk=self.submission_pk
            )
        except ESigningSubmission.DoesNotExist:
            return False

        if user.role in (User.Role.ADMIN,):
            return True
        if user.role == User.Role.AGENT:
            return sub.lease.unit.property.agent_id == user.pk or sub.created_by_id == user.pk
        if user.role == User.Role.TENANT:
            return sub.lease.co_tenants.filter(person__user=user).exists() or (
                sub.lease.primary_tenant and sub.lease.primary_tenant.user_id == user.pk
            )
        return False

    @database_sync_to_async
    def _get_submission_state(self):
        from .models import ESigningSubmission

        try:
            sub = ESigningSubmission.objects.get(pk=self.submission_pk)
        except ESigningSubmission.DoesNotExist:
            return None

        current_signer = None
        completed_signers = []
        pending_signers = []

        for s in sub.signers or []:
            st = (s.get("status") or "").lower()
            if st in ("completed", "signed"):
                completed_signers.append(s)
            elif current_signer is None and st not in ("declined",):
                current_signer = s
            else:
                pending_signers.append(s)

        return {
            "submission_id": sub.pk,
            "status": sub.status,
            "signing_mode": sub.signing_mode,
            "signers": sub.signers,
            "current_signer": current_signer,
            "completed_count": len(completed_signers),
            "total_signers": len(sub.signers or []),
            "signed_pdf_url": sub.signed_pdf_url or None,
        }


class ESigningAgentNotificationsConsumer(AsyncWebsocketConsumer):
    """
    Global signing notification channel for authenticated agents/admins.

    Connects to:  ws/esigning/notifications/
    Group name:   signing_notifications_<user_pk>

    Receives ``signing_notification`` events broadcast by
    ``webhooks._broadcast_agent_notification`` when any signer on any
    submission belonging to this agent completes or when a submission is
    fully completed.

    The frontend composable ``useGlobalSigningNotifications`` connects here
    on app mount and fires a toast for every event it receives, deduplicating
    by ``event_id``.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"signing_notifications_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Clients send ``{"action": "ping"}`` to keep connection alive — no-op."""
        pass

    # ── Group-broadcast handler ──────────────────────────────────────────

    async def signing_notification(self, event):
        """Forward a signing notification event to the connected admin client."""
        await self.send(text_data=json.dumps(event["payload"]))

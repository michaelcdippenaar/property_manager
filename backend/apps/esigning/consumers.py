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
            sub = ESigningSubmission.objects.select_related(
                "lease__unit__property", "mandate__property"
            ).get(pk=self.submission_pk)
        except ESigningSubmission.DoesNotExist:
            return False

        if user.role in (User.Role.ADMIN,) or getattr(user, "is_superuser", False):
            return True

        # Resolve the underlying property + agency for either a lease-bound or
        # mandate-only submission.
        prop = None
        sub_agency_id = getattr(sub, "agency_id", None)
        if sub.lease_id and sub.lease and sub.lease.unit_id:
            prop = sub.lease.unit.property
        elif sub.mandate_id and sub.mandate:
            prop = sub.mandate.property

        staff_roles = (
            User.Role.AGENT,
            User.Role.ESTATE_AGENT,
            User.Role.MANAGING_AGENT,
            User.Role.AGENCY_ADMIN,
        )
        if user.role in staff_roles:
            if sub.created_by_id == user.pk:
                return True
            user_agency_id = getattr(user, "agency_id", None)
            if user.role in (User.Role.AGENCY_ADMIN, User.Role.MANAGING_AGENT):
                # Agency-wide reach
                if user_agency_id and sub_agency_id and user_agency_id == sub_agency_id:
                    return True
                if prop is not None and user_agency_id and prop.agency_id == user_agency_id:
                    return True
                return False
            # Individual agent — must be the property's agent
            if prop is not None and prop.agent_id == user.pk:
                return True
            return False

        if user.role == User.Role.TENANT:
            if not sub.lease_id or not sub.lease:
                return False
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
            # Field name from the DocuSeal era was `signed_pdf_url` (a TextField
            # holding an external URL). After the native-signing migration (0010)
            # the column was dropped in favour of `signed_pdf_file` (FileField).
            # Build the URL from the file on the fly for backwards-compatible
            # WebSocket state payloads.
            "signed_pdf_url": sub.signed_pdf_file.url if sub.signed_pdf_file else None,
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

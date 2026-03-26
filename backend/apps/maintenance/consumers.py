"""
WebSocket consumer for per-issue maintenance chat.

This provides a real-time activity feed for each MaintenanceRequest.
Both admin/agent users and tenants can post messages. The AI assistant
only responds when explicitly invoked with @agent in the message.

The same chat data is accessible via REST API (GET/POST /maintenance/{id}/activity/)
for the mobile Flutter app, keeping both channels in sync.

WebSocket URL: ws://host/ws/maintenance/{pk}/activity/
"""
import json
import logging
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

# Pattern to detect @agent mention (case-insensitive, word boundary)
_AGENT_MENTION_RE = re.compile(r"@agent\b", re.IGNORECASE)


class MaintenanceActivityConsumer(AsyncWebsocketConsumer):
    """
    Real-time maintenance issue chat via WebSocket.

    Features:
      - Broadcasts activity to all connected clients (admin + tenant)
      - Sends existing activity history on connect
      - Admin/agent posts do NOT trigger AI response (ticket chat, not bot chat)
      - Only messages containing @agent trigger an AI response
      - AI responses are broadcast to all connected clients
    """

    async def connect(self):
        self.pk = self.scope["url_route"]["kwargs"]["pk"]
        self.group_name = f"maintenance_activity_{self.pk}"
        user = self.scope.get("user")

        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send existing activity history on connect
        activities = await self.get_activities()
        await self.send(text_data=json.dumps({"type": "history", "activities": activities}))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = (data.get("message") or "").strip()
        activity_type = data.get("activity_type", "note")

        if not message:
            return

        # Save the human message
        activity = await self.save_activity(message, activity_type)
        if not activity:
            return

        # Broadcast to the whole group
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "activity.message",
                "activity": activity,
            },
        )

        # Check for @agent mention — trigger AI response if found
        if _AGENT_MENTION_RE.search(message):
            await self._handle_agent_mention(message)

    async def activity_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "activity",
            "activity": event["activity"],
        }))

    async def _handle_agent_mention(self, message: str):
        """
        When @agent is mentioned, call Claude with the maintenance request
        context and recent chat history, then broadcast the AI response.
        """
        try:
            ai_response = await self._call_agent_ai(message)
            if ai_response:
                # Save AI response as a system activity
                activity = await self.save_activity(
                    ai_response,
                    "system",
                    is_ai=True,
                )
                if activity:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            "type": "activity.message",
                            "activity": activity,
                        },
                    )
        except Exception:
            logger.exception("Error handling @agent mention for request #%s", self.pk)

    @database_sync_to_async
    def _call_agent_ai(self, message: str) -> str | None:
        """
        Call Claude with maintenance request context + recent activity history.

        Returns the AI reply text or None on failure.
        """
        import anthropic
        from apps.leases.template_views import _get_anthropic_api_key
        from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest
        from core.anthropic_web_fetch import extract_anthropic_assistant_text
        from core.contract_rag import query_agent_qa, query_contracts

        api_key = _get_anthropic_api_key()
        if not api_key:
            return None

        try:
            req = MaintenanceRequest.objects.select_related(
                "unit__property", "supplier", "tenant"
            ).get(pk=self.pk)
        except MaintenanceRequest.DoesNotExist:
            return None

        # Build context from request + recent activities
        activities = (
            MaintenanceActivity.objects.filter(request=req)
            .select_related("created_by")
            .order_by("-created_at")[:20]
        )
        chat_lines = "\n".join(
            f"[{a.created_by.full_name if a.created_by else 'System'} "
            f"({a.created_by.role if a.created_by else 'ai'})]: {a.message}"
            for a in reversed(list(activities))
        )

        # Query RAG for relevant context
        rag_text = query_contracts(message, n_results=5)
        qa_text = query_agent_qa(message, n_results=3)

        system = (
            "You are Tremly's AI assistant, responding in a maintenance issue chat thread.\n"
            "You were mentioned with @agent by a participant in this maintenance ticket.\n\n"
            "Keep responses concise and practical. Focus on the maintenance issue at hand.\n"
            "Do NOT use markdown formatting. Write plain text only.\n\n"
            f"--- MAINTENANCE REQUEST ---\n"
            f"ID: #{req.pk}\n"
            f"Title: {req.title}\n"
            f"Description: {req.description}\n"
            f"Priority: {req.priority} | Category: {req.category} | Status: {req.status}\n"
            f"Unit: {req.unit.unit_number} — {req.unit.property.name}\n"
            f"Reported by: {req.tenant.full_name}\n"
            f"Assigned supplier: {req.supplier.display_name if req.supplier else 'Unassigned'}\n\n"
            f"--- RECENT CHAT ---\n{chat_lines or '(No messages yet)'}\n"
        )
        if rag_text:
            system += f"\n--- DOCUMENT EXCERPTS ---\n{rag_text}\n"
        if qa_text:
            system += f"\n--- STAFF Q&A ---\n{qa_text}\n"

        # Strip @agent from the message for the AI
        clean_msg = _AGENT_MENTION_RE.sub("", message).strip() or message

        client = anthropic.Anthropic(api_key=api_key, max_retries=2)
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": clean_msg}],
            )
        except Exception:
            logger.exception("AI error for @agent in request #%s", self.pk)
            return None

        return extract_anthropic_assistant_text(response).strip() or None

    @database_sync_to_async
    def get_activities(self):
        from .models import MaintenanceActivity
        from .serializers import MaintenanceActivitySerializer
        qs = MaintenanceActivity.objects.filter(request_id=self.pk).select_related("created_by")
        return MaintenanceActivitySerializer(qs, many=True).data

    @database_sync_to_async
    def save_activity(self, message, activity_type, is_ai=False):
        from .models import MaintenanceActivity, MaintenanceRequest
        from .serializers import MaintenanceActivitySerializer
        try:
            req = MaintenanceRequest.objects.get(pk=self.pk)
        except MaintenanceRequest.DoesNotExist:
            return None
        activity = MaintenanceActivity.objects.create(
            request=req,
            activity_type=activity_type,
            message=message,
            created_by=None if is_ai else self.user,
            metadata={"source": "ai_agent"} if is_ai else None,
        )
        return MaintenanceActivitySerializer(activity).data

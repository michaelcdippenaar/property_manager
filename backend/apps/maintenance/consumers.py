import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class MaintenanceActivityConsumer(AsyncWebsocketConsumer):

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

        activity = await self.save_activity(message, activity_type)

        # Broadcast to the whole group
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "activity.message",
                "activity": activity,
            },
        )

    async def activity_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "activity",
            "activity": event["activity"],
        }))

    @database_sync_to_async
    def get_activities(self):
        from .models import MaintenanceActivity
        from .serializers import MaintenanceActivitySerializer
        qs = MaintenanceActivity.objects.filter(request_id=self.pk).select_related("created_by")
        return MaintenanceActivitySerializer(qs, many=True).data

    @database_sync_to_async
    def save_activity(self, message, activity_type):
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
            created_by=self.user,
        )
        return MaintenanceActivitySerializer(activity).data

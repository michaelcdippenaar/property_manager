from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Global agent notification channel — must be listed BEFORE the pk route so
    # the literal "notifications" segment is matched first.
    re_path(r"ws/esigning/notifications/$", consumers.ESigningAgentNotificationsConsumer.as_asgi()),
    re_path(r"ws/esigning/(?P<pk>\d+)/$", consumers.ESigningStatusConsumer.as_asgi()),
]

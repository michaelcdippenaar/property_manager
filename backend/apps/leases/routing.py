"""WebSocket URL routes for the leases app."""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/leases/updates/$", consumers.LeaseUpdatesConsumer.as_asgi()),
]

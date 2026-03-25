from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/maintenance/(?P<pk>\d+)/activity/$", consumers.MaintenanceActivityConsumer.as_asgi()),
]

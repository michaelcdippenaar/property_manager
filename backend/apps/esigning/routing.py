from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/esigning/(?P<pk>\d+)/$", consumers.ESigningStatusConsumer.as_asgi()),
]

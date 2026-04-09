import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from apps.maintenance.routing import websocket_urlpatterns as maintenance_ws
from apps.esigning.routing import websocket_urlpatterns as esigning_ws
from apps.leases.routing import websocket_urlpatterns as leases_ws
from apps.maintenance.middleware import JwtAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddleware(
            URLRouter(maintenance_ws + esigning_ws + leases_ws)
        )
    ),
})

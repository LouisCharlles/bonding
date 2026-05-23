"""
ASGI config for setup project.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from bonding.middleware import JwtAuthMiddleware
from bonding.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddleware(
            URLRouter(websocket_urlpatterns),
        )
    ),
})

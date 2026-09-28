"""
ASGI config for setup project.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings")

# get_asgi_application() runs django.setup(), populating the app registry —
# it must happen before importing anything (like bonding.middleware) that
# touches Django models at module level, or it fails with
# "AppRegistryNotReady: Apps aren't loaded yet."
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from bonding.middleware import JwtAuthMiddleware
from bonding.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddleware(
            URLRouter(websocket_urlpatterns),
        )
    ),
})

from django.urls import path

from .consumers import ConversationConsumer, PresenceConsumer, StoriesConsumer


websocket_urlpatterns = [
    path("ws/presence/", PresenceConsumer.as_asgi()),
    path("ws/stories/", StoriesConsumer.as_asgi()),
    path("ws/conversations/<int:conversation_id>/", ConversationConsumer.as_asgi()),
]

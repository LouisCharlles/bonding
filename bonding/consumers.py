from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q

from .models import Conversation, Match
from .services.presence import touch_user_presence


@database_sync_to_async
def get_conversation_for_user(conversation_id, user):
    return Conversation.objects.filter(
        id=conversation_id,
    ).filter(
        Q(user1=user) | Q(user2=user),
    ).first()


@database_sync_to_async
def get_matched_user_ids(user):
    matches = Match.objects.filter(Q(user1=user) | Q(user2=user), is_active=True)
    user_ids = []
    for match in matches:
        user_ids.append(match.user2_id if match.user1_id == user.id else match.user1_id)
    return user_ids


class BaseEventConsumer(AsyncJsonWebsocketConsumer):
    group_name: str | None = None

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        await self.accept()

        if self.group_name:
            await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def broadcast_event(self, event):
        await self.send_json(event["event"])


class PresenceConsumer(BaseEventConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = "presence_global"
        await super().connect()
        await database_sync_to_async(touch_user_presence)(user, active=True)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast.event",
                "event": {
                    "type": "presence.updated",
                    "entity": "presence",
                    "data": {
                        "user_id": user.id,
                        "is_online": True,
                    },
                },
            },
        )

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if user and user.is_authenticated:
            await database_sync_to_async(touch_user_presence)(user, active=False)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "broadcast.event",
                    "event": {
                        "type": "presence.updated",
                        "entity": "presence",
                        "data": {
                            "user_id": user.id,
                            "is_online": False,
                        },
                    },
                },
            )
        await super().disconnect(close_code)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await database_sync_to_async(touch_user_presence)(self.scope["user"], active=True)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "broadcast.event",
                    "event": {
                        "type": "presence.updated",
                        "entity": "presence",
                        "data": {
                            "user_id": self.scope["user"].id,
                            "is_online": True,
                        },
                    },
                },
            )
            await self.send_json({"type": "pong"})


class ConversationConsumer(BaseEventConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        conversation = await get_conversation_for_user(conversation_id, user)
        if not conversation:
            await self.close(code=4403)
            return

        self.conversation_id = conversation_id
        self.group_name = f"conversation_{conversation_id}"
        await super().connect()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})


class StoriesConsumer(BaseEventConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = f"stories_{user.id}"
        await super().connect()

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

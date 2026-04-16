from django.db import models
from django.db.models import Q
from .conversation import Conversation
from .user import User
from ..storage import get_photo_storage


class Message(models.Model):
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_STORY_REPLY = "story_reply"

    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    message_type = models.CharField(
        max_length=20,
        choices=[
            (TYPE_TEXT, "Texto"),
            (TYPE_IMAGE, "Imagem"),
            (TYPE_VIDEO, "Video"),
            (TYPE_STORY_REPLY, "Resposta de story"),
        ],
        default=TYPE_TEXT,
    )
    media = models.FileField(
        upload_to="message_media/",
        storage=get_photo_storage(),
        blank=True,
        null=True,
    )
    story = models.ForeignKey(
        "bonding.Story",
        related_name="message_replies",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    reply_to_message = models.ForeignKey(
        "self",
        related_name="thread_replies",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    is_view_once = models.BooleanField(default=False)
    client_request_id = models.CharField(max_length=64, blank=True, null=True)
    consumed_at = models.DateTimeField(blank=True, null=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "client_request_id"],
                condition=Q(client_request_id__isnull=False),
                name="bonding_message_sender_client_request_id_uniq",
            ),
        ]

    def __str__(self):
        return f"Message {self.id} in conversation {self.conversation_id}"


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, related_name="reactions", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="message_reactions", on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")
        ordering = ["-created_at"]

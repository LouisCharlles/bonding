from django.db import models
from .conversation import Conversation
from .user import User
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)

    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    read = models.BooleanField(default=False)
    class Meta:
        ordering = ['created_at']
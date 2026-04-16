from django.conf import settings
from django.db import models


class Match(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="matches_as_user1",
        on_delete=models.CASCADE,
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="matches_as_user2",
        on_delete=models.CASCADE,
    )
    conversation = models.OneToOneField(
        "bonding.Conversation",
        related_name="match",
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user1", "user2")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Match {self.user1_id}-{self.user2_id}"

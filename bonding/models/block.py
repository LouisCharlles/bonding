from django.conf import settings
from django.db import models


class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocks_sent",
        on_delete=models.CASCADE,
    )
    blocked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocks_received",
        on_delete=models.CASCADE,
    )
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocker", "blocked_user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.blocker_id}->{self.blocked_user_id}"

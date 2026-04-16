from django.conf import settings
from django.db import models


class VideoCallSession(models.Model):
    STATUS_REQUESTED = "requested"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_FINISHED = "finished"

    conversation = models.ForeignKey(
        "bonding.Conversation",
        related_name="video_calls",
        on_delete=models.CASCADE,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="video_calls_started",
        on_delete=models.CASCADE,
    )
    room_name = models.CharField(max_length=120, unique=True)
    provider = models.CharField(max_length=40, default="webrtc")
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_REQUESTED, "Solicitada"),
            (STATUS_ACCEPTED, "Aceita"),
            (STATUS_DECLINED, "Recusada"),
            (STATUS_FINISHED, "Finalizada"),
        ],
        default=STATUS_REQUESTED,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.room_name

from django.conf import settings
from django.db import models


class PushDevice(models.Model):
    PROVIDER_FCM = "fcm"
    PROVIDER_EXPO = "expo"
    PROVIDER_WEB_PUSH = "web_push"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="push_devices",
        on_delete=models.CASCADE,
    )
    token = models.CharField(max_length=255, unique=True)
    provider = models.CharField(
        max_length=20,
        choices=[
            (PROVIDER_FCM, "Firebase"),
            (PROVIDER_EXPO, "Expo"),
            (PROVIDER_WEB_PUSH, "Web Push"),
        ],
        default=PROVIDER_FCM,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.provider}"

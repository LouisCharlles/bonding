import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_password_reset_expiration():
    return timezone.now() + timedelta(minutes=30)


class PasswordResetToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_token",
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_password_reset_expiration)

    def is_valid(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"Token de redefinição para {self.user.email}"

from django.conf import settings
from django.db import models


class UserLocationPing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="location_pings",
        on_delete=models.CASCADE,
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy_meters = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

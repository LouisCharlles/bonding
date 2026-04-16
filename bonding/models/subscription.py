from django.conf import settings
from django.db import models


class Subscription(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    plan = models.ForeignKey(
        "bonding.PremiumPlan",
        related_name="subscriptions",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PENDING, "Pendente"),
            (STATUS_ACTIVE, "Ativa"),
            (STATUS_CANCELED, "Cancelada"),
            (STATUS_EXPIRED, "Expirada"),
        ],
        default=STATUS_PENDING,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

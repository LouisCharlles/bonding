from django.conf import settings
from django.db import models


class Report(models.Model):
    STATUS_OPEN = "open"
    STATUS_REVIEWING = "reviewing"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"

    REASON_SPAM = "spam"
    REASON_FAKE = "fake"
    REASON_ABUSE = "abuse"
    REASON_INAPPROPRIATE = "inappropriate"
    REASON_OTHER = "other"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reports_sent",
        on_delete=models.CASCADE,
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reports_received",
        on_delete=models.CASCADE,
    )
    reason = models.CharField(
        max_length=30,
        choices=[
            (REASON_SPAM, "Spam"),
            (REASON_FAKE, "Perfil falso"),
            (REASON_ABUSE, "Abuso"),
            (REASON_INAPPROPRIATE, "Conteudo inapropriado"),
            (REASON_OTHER, "Outro"),
        ],
    )
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_OPEN, "Aberto"),
            (STATUS_REVIEWING, "Em revisao"),
            (STATUS_RESOLVED, "Resolvido"),
            (STATUS_DISMISSED, "Descartado"),
        ],
        default=STATUS_OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.id}"

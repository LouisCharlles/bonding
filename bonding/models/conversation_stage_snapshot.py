from django.db import models


class ConversationStageSnapshot(models.Model):
    STAGE_QUEBRA_GELO = "quebra_gelo"
    STAGE_RAPPORT = "rapport"
    STAGE_INTERESSE_MUTUO = "interesse_mutuo"
    STAGE_PRONTO_PARA_ROLE = "pronto_para_role"
    STAGE_CHOICES = [
        (STAGE_QUEBRA_GELO, "Quebra-gelo"),
        (STAGE_RAPPORT, "Rapport"),
        (STAGE_INTERESSE_MUTUO, "Interesse mútuo"),
        (STAGE_PRONTO_PARA_ROLE, "Pronto para rolê"),
    ]

    READY_STAGES = (STAGE_INTERESSE_MUTUO, STAGE_PRONTO_PARA_ROLE)

    conversation = models.OneToOneField(
        "bonding.Conversation",
        related_name="stage_snapshot",
        on_delete=models.CASCADE,
    )
    stage = models.CharField(max_length=32, choices=STAGE_CHOICES, default=STAGE_QUEBRA_GELO)
    stage_confidence = models.PositiveSmallIntegerField(default=0)
    interests = models.JSONField(default=list, blank=True)
    tipo_role = models.CharField(max_length=32, blank=True, null=True)
    last_suggested_at = models.DateTimeField(null=True, blank=True)
    last_suggested_message_count = models.PositiveIntegerField(default=0)
    cached_suggestions = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

from django.db import models


class DateSuggestionFeedback(models.Model):
    EVENT_SHOWN = "shown"
    EVENT_CHOICES = [
        (EVENT_SHOWN, "Shown"),
    ]

    SOURCE_AUTOMATIC = "automatic"
    SOURCE_MANUAL = "manual"
    SOURCE_EXPERIMENT = "experiment"

    VARIANT_AI_PURE = "ai_pure"
    VARIANT_DETERMINISTIC_PURE = "deterministic_pure"
    VARIANT_HYBRID_FULL = "hybrid_full"
    VARIANT_HYBRID_SIMPLE_PROMPT = "hybrid_control_simple_prompt"
    VARIANT_CHOICES = [
        (VARIANT_AI_PURE, "IA Pura"),
        (VARIANT_DETERMINISTIC_PURE, "Determinística Pura"),
        (VARIANT_HYBRID_FULL, "Híbrida Completa"),
        (VARIANT_HYBRID_SIMPLE_PROMPT, "Híbrida de Controle (prompt simplificado)"),
    ]

    conversation = models.ForeignKey(
        "bonding.Conversation",
        related_name="date_suggestion_feedback",
        on_delete=models.CASCADE,
    )
    match = models.ForeignKey(
        "bonding.Match",
        related_name="date_suggestion_feedback",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=10, choices=EVENT_CHOICES, default=EVENT_SHOWN)
    place_name = models.CharField(max_length=255)
    place_latitude = models.FloatField(null=True, blank=True)
    place_longitude = models.FloatField(null=True, blank=True)
    deterministic_score = models.FloatField(null=True, blank=True)
    llm_score = models.FloatField(null=True, blank=True)
    llm_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    metadata_completeness_score = models.FloatField(null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=[
            (SOURCE_AUTOMATIC, "Automatic"),
            (SOURCE_MANUAL, "Manual"),
            (SOURCE_EXPERIMENT, "Experiment"),
        ],
        default=SOURCE_AUTOMATIC,
    )
    variant = models.CharField(max_length=40, choices=VARIANT_CHOICES, null=True, blank=True, db_index=True)
    experiment_run_id = models.CharField(max_length=36, null=True, blank=True, db_index=True)
    round_id = models.CharField(max_length=36, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
        ]

    def __str__(self):
        return f"DateSuggestionFeedback {self.place_name} (conversation {self.conversation_id})"

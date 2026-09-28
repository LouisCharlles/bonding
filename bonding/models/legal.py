import hashlib

from django.db import models
from django.utils import timezone


class LegalDocumentVersion(models.Model):
    TERMS_OF_USE = "terms_of_use"
    PRIVACY_POLICY = "privacy_policy"
    RESEARCH_CONSENT = "research_consent"

    document_type_choices = [
        (TERMS_OF_USE, "Termos de Uso"),
        (PRIVACY_POLICY, "Politica de Privacidade"),
        (RESEARCH_CONSENT, "Termo de Consentimento Livre e Esclarecido (TCLE)"),
    ]

    document_type = models.CharField(max_length=32, choices=document_type_choices)
    version_label = models.CharField(max_length=32)
    content = models.TextField()
    content_hash = models.CharField(max_length=64, editable=False, blank=True)
    is_current = models.BooleanField(default=False)
    effective_date = models.DateField()
    published_at = models.DateTimeField(default=timezone.now)
    dpo_contact_snapshot = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Contato do Encarregado (DPO) vigente na publicacao desta versao. "
            "TODO: preencher quando houver Encarregado formalmente definido."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type"],
                condition=models.Q(is_current=True),
                name="unique_current_legal_document_per_type",
            )
        ]
        ordering = ["document_type", "-published_at"]

    def save(self, *args, **kwargs):
        self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_document_type_display()} v{self.version_label}"

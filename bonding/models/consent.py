from django.db import models

from .user import User


class ConsentRecord(models.Model):
    """Log de consentimento append-only. Nunca deve ser editado/apagado — ver
    trigger de banco criada na migration 0019 e bonding/services/consent.py."""

    GENERAL_TERMS = "general_terms"
    PRIVACY_POLICY = "privacy_policy"
    BIOMETRIC_VERIFICATION = "biometric_verification"
    PRECISE_GEOLOCATION = "precise_geolocation"
    SENSITIVE_PROFILE_DATA = "sensitive_profile_data"
    ACCOUNT_DEACTIVATION = "account_deactivation"
    ACCOUNT_DELETION = "account_deletion"
    ACCOUNT_REACTIVATION = "account_reactivation"
    RESEARCH_CONSENT = "research_consent"

    consent_type_choices = [
        (GENERAL_TERMS, "Termos de Uso"),
        (PRIVACY_POLICY, "Politica de Privacidade"),
        (BIOMETRIC_VERIFICATION, "Verificacao biometrica facial"),
        (PRECISE_GEOLOCATION, "Geolocalizacao precisa"),
        (SENSITIVE_PROFILE_DATA, "Dado sensivel de perfil (genero/orientacao sexual)"),
        (ACCOUNT_DEACTIVATION, "Desativacao de conta solicitada pelo usuario"),
        (ACCOUNT_DELETION, "Exclusao de conta solicitada pelo usuario"),
        (ACCOUNT_REACTIVATION, "Reativacao de conta via novo login"),
        (RESEARCH_CONSENT, "TCLE - participacao na pesquisa academica"),
    ]

    ACTION_GRANTED = "granted"
    ACTION_REVOKED = "revoked"

    action_choices = [
        (ACTION_GRANTED, "Concedido"),
        (ACTION_REVOKED, "Revogado"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="consent_records")
    document_version = models.ForeignKey(
        "LegalDocumentVersion",
        on_delete=models.PROTECT,
        related_name="consent_records",
        null=True,
        blank=True,
    )
    consent_type = models.CharField(max_length=32, choices=consent_type_choices)
    action = models.CharField(max_length=10, choices=action_choices, default=ACTION_GRANTED)
    granted_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Cadeia de integridade (hash-chain global + HMAC) — ver bonding/services/consent.py
    prev_hash = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64)
    hmac_signature = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"user={self.user_id} {self.consent_type} {self.action} @ {self.granted_at}"

from django.db import models

from .profile import Profile
from ..storage import get_photo_storage


class ProfileVerificationAttempt(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_REVIEW = "review"

    profile = models.ForeignKey(
        Profile,
        related_name="verification_attempts",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PENDING, "Pendente"),
            (STATUS_APPROVED, "Aprovado"),
            (STATUS_REJECTED, "Rejeitado"),
            (STATUS_REVIEW, "Em revisao"),
        ],
        default=STATUS_PENDING,
    )
    score = models.FloatField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    provider = models.CharField(max_length=40, default="aws_rekognition")
    provider_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class VerificationSelfie(models.Model):
    attempt = models.OneToOneField(
        ProfileVerificationAttempt,
        related_name="selfie",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="verification_selfies/", storage=get_photo_storage())
    brightness_score = models.FloatField(blank=True, null=True)
    face_detected = models.BooleanField(default=False)
    accessories_detected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

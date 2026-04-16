from django.conf import settings
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="wallet",
        on_delete=models.CASCADE,
    )
    ribbons_balance = models.PositiveIntegerField(default=0)
    hearts_balance = models.PositiveIntegerField(default=0)
    rewinds_balance = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet {self.user_id}"


class WalletLedger(models.Model):
    TYPE_REWARD = "reward"
    TYPE_SPEND = "spend"
    TYPE_CONVERSION = "conversion"
    TYPE_UNLOCK = "unlock"

    wallet = models.ForeignKey(Wallet, related_name="entries", on_delete=models.CASCADE)
    entry_type = models.CharField(
        max_length=20,
        choices=[
            (TYPE_REWARD, "Reward"),
            (TYPE_SPEND, "Spend"),
            (TYPE_CONVERSION, "Conversion"),
            (TYPE_UNLOCK, "Unlock"),
        ],
    )
    ribbons_delta = models.IntegerField(default=0)
    hearts_delta = models.IntegerField(default=0)
    rewinds_delta = models.IntegerField(default=0)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RewardEvent(models.Model):
    KIND_DAILY_LIKE = "daily_like"
    KIND_VIDEO = "video"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reward_events",
        on_delete=models.CASCADE,
    )
    kind = models.CharField(
        max_length=30,
        choices=[(KIND_DAILY_LIKE, "Curtida diaria"), (KIND_VIDEO, "Video")],
    )
    awarded_ribbons = models.PositiveIntegerField(default=0)
    awarded_hearts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class UnlockSession(models.Model):
    TARGET_LIKES = "likes_received"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="unlock_sessions",
        on_delete=models.CASCADE,
    )
    target = models.CharField(max_length=40, default=TARGET_LIKES)
    unlocked_until = models.DateTimeField()
    ribbons_spent = models.PositiveIntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

from django.db import models


class PremiumPlan(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2)
    likes_per_day = models.PositiveIntegerField(default=100)
    can_see_who_liked = models.BooleanField(default=False)
    has_unlimited_swipes = models.BooleanField(default=False)
    has_priority_boost = models.BooleanField(default=False)
    has_video_calls = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_monthly"]

    def __str__(self):
        return self.name

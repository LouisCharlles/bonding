from django.db import models
from .user import User


class Connection(models.Model):
    STATUS_LIKE = "like"
    STATUS_PASS = "pass"
    STATUS_SUPERLIKE = "superlike"

    STATUS_CHOICES = [
        (STATUS_LIKE, "Like"),
        (STATUS_PASS, "Pass"),
        (STATUS_SUPERLIKE, "Super Like"),
    ]

    from_user = models.ForeignKey(
        User,
        related_name='likes_sent',
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        User,
        related_name='likes_received',
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_mutual = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        verbose_name = "Like/Dislike"
        verbose_name_plural = "Likes/Dislikes"

    def __str__(self):
        return f"{self.from_user.email} -> {self.to_user.email} ({self.status})"

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from ..storage import get_photo_storage


def default_story_expiration():
    return timezone.now() + timedelta(hours=24)


class Story(models.Model):
    VISIBILITY_MATCHES = "matches"
    VISIBILITY_ALL = "all"
    MEDIA_IMAGE = "image"
    MEDIA_VIDEO = "video"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="stories",
        on_delete=models.CASCADE,
    )
    media_type = models.CharField(
        max_length=10,
        choices=[(MEDIA_IMAGE, "Imagem"), (MEDIA_VIDEO, "Video")],
        default=MEDIA_IMAGE,
    )
    media = models.FileField(upload_to="stories/", storage=get_photo_storage())
    caption = models.CharField(max_length=255, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=[(VISIBILITY_MATCHES, "Matches"), (VISIBILITY_ALL, "Todos")],
        default=VISIBILITY_MATCHES,
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(default=default_story_expiration)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Story {self.id} by {self.author_id}"


class StoryView(models.Model):
    story = models.ForeignKey(Story, related_name="views", on_delete=models.CASCADE)
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="story_views",
        on_delete=models.CASCADE,
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("story", "viewer")
        ordering = ["-viewed_at"]


class StoryReaction(models.Model):
    story = models.ForeignKey(Story, related_name="reactions", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="story_reactions",
        on_delete=models.CASCADE,
    )
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("story", "user", "emoji")
        ordering = ["-created_at"]

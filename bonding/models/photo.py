from django.db import models
from django.db.models import Q
from .profile import Profile
from ..storage import get_photo_storage


class Photo(models.Model):
    profile = models.ForeignKey(Profile, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_gallery/', storage=get_photo_storage())
    description = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    client_request_id = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "client_request_id"],
                condition=Q(client_request_id__isnull=False),
                name="bonding_photo_profile_client_request_id_uniq",
            ),
        ]

    def __str__(self):
        return f"Photo {self.id} of {self.profile.name}"

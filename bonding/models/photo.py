from django.db import models
from .profile import Profile
class Photo(models.Model):
    profile = models.ForeignKey(Profile,related_name='photos',on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_gallery/')
    description = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Photo {self.id} of {self.profile.name}"
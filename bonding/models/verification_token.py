import uuid
from django.db import models
from django.utils import timezone
from .user import User

User = User()

class VerificationToken(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='verification_token')

    token = models.UUIDField(default=uuid.uuid4,editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    def is_valid(self):
        return self.expires_at > timezone.now()
    
    def __str__(self):
        return f"Token de verificação para {self.user.email}"
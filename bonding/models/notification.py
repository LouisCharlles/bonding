from django.db import models
from .user import User


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('NEW_MESSAGE', 'Nova Mensagem'),
        ('NEW_CONNECTION', 'Nova Conexao'),
        ('NEW_MATCH', 'Novo Match'),
        ('LIKE_RECEIVED', 'Voce recebeu um Like'),
        ('PROFILE_VERIFIED', 'Perfil verificado'),
        ('VIDEO_CALL_INVITE', 'Convite para videochamada'),
        ('PREMIUM_UPDATED', 'Plano premium atualizado'),
    ]

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    created_at = models.DateTimeField(auto_now_add=True,null=False,blank=False)

    read = models.BooleanField(default=False)

    recipient = models.ForeignKey(User,on_delete=models.CASCADE,related_name="notifications")

    message = models.TextField()

    target_object_id = models.CharField(max_length=255,blank=True,null=True)

    def set_as_read(self):
        self.read = True
        self.save()

    class Meta:
        ordering = ['-created_at']

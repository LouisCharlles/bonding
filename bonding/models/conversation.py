from django.db import models
from .user import User

class Conversation(models.Model):
    user1 = models.ForeignKey(User,related_name='conversations_as_user1',on_delete=models.CASCADE)

    user2 = models.ForeignKey(User,related_name='conversations_as_user2',on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    last_message = models.TextField(blank=True, null=True)

    class Meta:
        #Garante que um match entre A e B seja o mesmo que B e A.
        #O Django ordena as chaves internamente para garantir a unicidade.
        unique_together = ('user1','user2')


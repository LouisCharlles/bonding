from django.db import models
from .user import User
class Connection(models.Model):
    from_user = models.ForeignKey(User,
    related_name='likes_sent',
    on_delete=models.CASCADE)

    to_user = models.ForeignKey(User,
    related_name='likes_received',
    on_delete=models.CASCADE)

    status = models.CharField(max_length=10,
    choices=[('Like',"Dislike")])

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        verbose_name = "Like/Dislike"
        verbose_name_plural = "Likes/Dislikes"

    
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Connection,Message,Notification,Conversation

@receiver(post_save,sender=Connection)
def notificar_usuarios_de_conexao_formada(sender,instance,created,**kwargs):
  if created and instance.status == 'Like':
    reciprocal_connection = Connection.objects.filter(
      from_user=instance.to_user,
      to_user=instance.from_user,
      status='Like'
    ).exists()

    if reciprocal_connection:
      Notification.objects.create(
        recipient=instance.from_user,
        notification_type="NEW_MATCH",
        message=f"Você e {instance.to_user.profile.name} deram match!",
        target_object_id=str(instance.to_user.id)
      )
      Notification.objects.create(
        recipient=instance.to_user,
        notification_type="NEW_MATCH",
        message=f"Você e {instance.from_user.profile.name} deram match!",
        target_object_id=str(instance.from_user.id)
      )

@receiver(post_save,sender=Message)
def notificar_usuario_nova_mensagem_na_conversa(sender,instance,created,**kwargs):
  if created:
    if instance.conversation.user1 == instance.sender:
      recipient = instance.conversation.user2
    else:
      recipient = instance.conversation.user1
   
    Notification.objects.create(
      recipient=recipient,
      notification_type="NEW_MESSAGE",
      message=f"Você recebeu uma nova mensagem de {instance.sender.profile.name}!",
      target_object_id=str(instance.conversation.id)
    )



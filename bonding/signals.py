from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Connection, Match, Message, Notification, Photo, Profile, User, Wallet


@receiver(post_save, sender=Profile)
def invalidate_profile_me_cache(sender, instance, **kwargs):
    # /profiles/me/ fica 5 min em cache; qualquer escrita no Profile (ex.:
    # aprovacao da verificacao facial) precisa derrubar a resposta antiga,
    # senao o frontend segue vendo is_verified=false e volta para /app/verify.
    cache.delete(f"profile_me:{instance.user_id}")


@receiver([post_save, post_delete], sender=Photo)
def invalidate_profile_me_cache_on_photo_change(sender, instance, **kwargs):
    user_id = Profile.objects.filter(pk=instance.profile_id).values_list("user_id", flat=True).first()
    if user_id is not None:
        cache.delete(f"profile_me:{user_id}")


@receiver(post_save, sender=Connection)
def notify_likes_and_matches(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.status in [Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE]:
        Notification.objects.create(
            recipient=instance.to_user,
            notification_type="LIKE_RECEIVED",
            message=f"{instance.from_user.profile.name} curtiu seu perfil.",
            target_object_id=str(instance.from_user.id),
        )


@receiver(post_save, sender=Match)
def notify_new_match(sender, instance, created, **kwargs):
    if not created:
        return

    Notification.objects.create(
        recipient=instance.user1,
        notification_type="NEW_MATCH",
        message=f"Voce deu match com {instance.user2.profile.name}.",
        target_object_id=str(instance.user2.id),
    )
    Notification.objects.create(
        recipient=instance.user2,
        notification_type="NEW_MATCH",
        message=f"Voce deu match com {instance.user1.profile.name}.",
        target_object_id=str(instance.user1.id),
    )


@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if not created:
        return

    recipient = (
        instance.conversation.user2
        if instance.conversation.user1 == instance.sender
        else instance.conversation.user1
    )
    Notification.objects.create(
        recipient=recipient,
        notification_type="NEW_MESSAGE",
        message=f"Voce recebeu uma nova mensagem de {instance.sender.profile.name}.",
        target_object_id=str(instance.conversation.id),
    )


@receiver(post_save, sender=User)
def ensure_wallet_for_user(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)




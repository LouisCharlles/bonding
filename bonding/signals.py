from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Connection, Match, Message, Notification, StoryReaction, User, Wallet


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


@receiver(post_save, sender=StoryReaction)
def notify_story_reaction(sender, instance, created, **kwargs):
    if not created or instance.story.author_id == instance.user_id:
        return

    Notification.objects.create(
        recipient=instance.story.author,
        notification_type="NEW_CONNECTION",
        message=f"{instance.user.profile.name} reagiu ao seu story com {instance.emoji}.",
        target_object_id=str(instance.story.id),
    )



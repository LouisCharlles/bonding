from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def publish_group_event(group_name: str, event: dict):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "broadcast.event",
            "event": event,
        },
    )


def publish_to_users(group_prefix: str, user_ids: list[int], event: dict):
    unique_ids = {user_id for user_id in user_ids if user_id}
    for user_id in unique_ids:
        publish_group_event(f"{group_prefix}_{user_id}", event)

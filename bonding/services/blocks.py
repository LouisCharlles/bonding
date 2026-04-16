from ..models import Block


def get_blocked_user_ids(user):
    sent = Block.objects.filter(blocker=user).values_list("blocked_user_id", flat=True)
    received = Block.objects.filter(blocked_user=user).values_list("blocker_id", flat=True)
    return set(sent).union(set(received))


def is_blocked_pair(user_a, user_b):
    return Block.objects.filter(
        blocker_id__in=[user_a.id, user_b.id],
        blocked_user_id__in=[user_a.id, user_b.id],
    ).exists()

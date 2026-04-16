from datetime import timedelta

from django.utils import timezone


ONLINE_WINDOW_SECONDS = 75


def is_profile_online(profile) -> bool:
    if not profile or not profile.is_online or not profile.last_seen:
        return False
    return profile.last_seen >= timezone.now() - timedelta(seconds=ONLINE_WINDOW_SECONDS)


def touch_user_presence(user, active: bool = True):
    profile = getattr(user, "profile", None)
    if not profile:
        return None

    profile.is_online = active
    if active:
        profile.last_seen = timezone.now()
        profile.save(update_fields=["is_online", "last_seen", "updated_at"])
    else:
        profile.save(update_fields=["is_online", "updated_at"])
    return profile

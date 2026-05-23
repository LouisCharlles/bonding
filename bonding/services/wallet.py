from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ..models import RewardEvent, UnlockSession, Wallet, WalletLedger


def get_or_create_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def _normalize_balances(wallet):
    if wallet.ribbons_balance >= 100:
        extra_hearts = wallet.ribbons_balance // 100
        wallet.ribbons_balance = wallet.ribbons_balance % 100
        wallet.hearts_balance += extra_hearts


@transaction.atomic
def award_daily_like_ribbon(user):
    today = timezone.localdate()
    if RewardEvent.objects.filter(
        user=user,
        kind=RewardEvent.KIND_DAILY_LIKE,
        created_at__date=today,
    ).exists():
        return False

    wallet = get_or_create_wallet(user)
    wallet.ribbons_balance += 1
    _normalize_balances(wallet)
    wallet.save(update_fields=["ribbons_balance", "hearts_balance", "updated_at"])
    RewardEvent.objects.create(user=user, kind=RewardEvent.KIND_DAILY_LIKE, awarded_ribbons=1)
    WalletLedger.objects.create(
        wallet=wallet,
        entry_type=WalletLedger.TYPE_REWARD,
        ribbons_delta=1,
        description="Recompensa diaria por curtida",
    )
    return True


@transaction.atomic
def award_video_ribbons(user, count=2):
    today = timezone.localdate()
    videos_today = RewardEvent.objects.filter(
        user=user,
        kind=RewardEvent.KIND_VIDEO,
        created_at__date=today,
    ).count()
    if videos_today >= 3:
        return False, "Limite diario de videos atingido."

    wallet = get_or_create_wallet(user)
    wallet.ribbons_balance += count
    _normalize_balances(wallet)
    wallet.save(update_fields=["ribbons_balance", "hearts_balance", "updated_at"])
    RewardEvent.objects.create(user=user, kind=RewardEvent.KIND_VIDEO, awarded_ribbons=count)
    WalletLedger.objects.create(
        wallet=wallet,
        entry_type=WalletLedger.TYPE_REWARD,
        ribbons_delta=count,
        description="Recompensa por video assistido",
    )
    return True, "Recompensa concedida."


@transaction.atomic
def consume_rewind_ribbon(user):
    from ..models import Profile
    profile = getattr(user, "profile", None)
    if profile and profile.premium_tier != Profile.PREMIUM_FREE:
        return
    wallet = get_or_create_wallet(user)
    wallet.refresh_from_db(fields=["ribbons_balance"])
    if wallet.ribbons_balance < 25:
        raise ValueError("Saldo insuficiente. Voce precisa de 25 lacos para reverter.")
    wallet.ribbons_balance -= 25
    _normalize_balances(wallet)
    wallet.save(update_fields=["ribbons_balance", "hearts_balance", "updated_at"])
    WalletLedger.objects.create(
        wallet=wallet,
        entry_type=WalletLedger.TYPE_SPEND,
        ribbons_delta=-25,
        description="Rewind: reverter ultima interacao",
    )


def can_unlock_likes_session(user):
    return UnlockSession.objects.filter(
        user=user,
        target=UnlockSession.TARGET_LIKES,
        unlocked_until__gt=timezone.now(),
    ).exists()


@transaction.atomic
def unlock_likes_session(user):
    wallet = get_or_create_wallet(user)
    if wallet.ribbons_balance < 50:
        raise ValueError("Voce precisa de 50 lacos para desbloquear curtidas.")

    wallet.ribbons_balance -= 50
    wallet.save(update_fields=["ribbons_balance", "updated_at"])
    unlock = UnlockSession.objects.create(
        user=user,
        target=UnlockSession.TARGET_LIKES,
        unlocked_until=timezone.now() + timedelta(hours=2),
        ribbons_spent=50,
    )
    WalletLedger.objects.create(
        wallet=wallet,
        entry_type=WalletLedger.TYPE_UNLOCK,
        ribbons_delta=-50,
        description="Desbloqueio temporario de curtidas recebidas",
        metadata={"unlock_session_id": unlock.id},
    )
    return unlock

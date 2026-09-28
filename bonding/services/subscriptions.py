from ..models import Profile, Subscription


def activate_demo_subscription(user, plan):
    """So usado quando settings.PAYMENTS_DEMO_MODE=True (piloto academico de
    TCC): ativa o plano premium imediatamente, sem cobranca real, espelhando
    o que o webhook do AbacatePay faria apos um pagamento de verdade."""
    subscription = Subscription.objects.create(
        user=user, plan=plan, status=Subscription.STATUS_ACTIVE
    )
    Profile.objects.filter(user=user).update(premium_tier=plan.code)
    return subscription

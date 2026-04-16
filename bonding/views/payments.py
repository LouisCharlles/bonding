import json

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PremiumPlan, Profile, Subscription
from ..services.external_integrations import IntegrationError, create_stripe_payment_intent, verify_stripe_signature


class StripePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        plan = PremiumPlan.objects.filter(id=plan_id, is_active=True).first()
        if not plan:
            return Response({"detail": "Plano invalido."}, status=404)

        try:
            intent = create_stripe_payment_intent(
                int(plan.price_monthly * 100),
                request.user.email,
                metadata={"user_id": request.user.id, "plan_id": plan.id},
            )
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        return Response({
            "payment_intent_id": intent.get("id"),
            "client_secret": intent.get("client_secret"),
        }, status=201)


class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payload = request.body
        signature = request.headers.get("Stripe-Signature")
        try:
            verify_stripe_signature(payload, signature)
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        event = json.loads(payload.decode("utf-8"))
        event_type = event.get("type")
        if event_type == "payment_intent.succeeded":
            metadata = event.get("data", {}).get("object", {}).get("metadata", {})
            user_id = metadata.get("user_id")
            plan_id = metadata.get("plan_id")
            plan = PremiumPlan.objects.filter(id=plan_id).first()
            if user_id and plan:
                subscription = Subscription.objects.create(
                    user_id=user_id,
                    plan=plan,
                    status=Subscription.STATUS_ACTIVE,
                )
                Profile.objects.filter(user_id=user_id).update(premium_tier=plan.code)
        return Response({"received": True}, status=200)

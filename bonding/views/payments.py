import json

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PremiumPlan, Profile, Subscription
from ..services.external_integrations import (
    IntegrationError,
    create_abacatepay_billing,
    create_abacatepay_pix,
    verify_abacatepay_webhook,
)


class AbacatePayIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        plan = PremiumPlan.objects.filter(id=plan_id, is_active=True).first()
        if not plan:
            return Response({"detail": "Plano invalido."}, status=404)

        amount = int(plan.price_monthly * 100)
        method = request.data.get("method", "card")
        cpf = request.data.get("cpf", "")

        if method == "pix" and not cpf:
            return Response({"detail": "CPF obrigatorio para pagamento via PIX."}, status=400)

        try:
            if method == "pix":
                result = create_abacatepay_pix(amount, request.user, plan, cpf)
                return Response({
                    "pix_code": result["pix_code"],
                    "qr_code_image": result["qr_code_image"],
                }, status=201)

            result = create_abacatepay_billing(amount, request.user, plan, cpf)
            return Response({"checkout_url": result["checkout_url"]}, status=201)

        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)


class AbacatePayWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.query_params.get("token", "")
        try:
            verify_abacatepay_webhook(token)
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        try:
            event = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({"detail": "Payload invalido."}, status=400)

        event_type = event.get("event")
        # Ambos billing.paid e pixQrCode.paid carregam metadata em event.data
        if event_type in ("billing.paid", "pixQrCode.paid"):
            metadata = event.get("data", {}).get("metadata", {})
            user_id = metadata.get("user_id")
            plan_id = metadata.get("plan_id")
            plan = PremiumPlan.objects.filter(id=plan_id).first()
            if user_id and plan:
                Subscription.objects.create(
                    user_id=user_id,
                    plan=plan,
                    status=Subscription.STATUS_ACTIVE,
                )
                Profile.objects.filter(user_id=user_id).update(premium_tier=plan.code)

        return Response({"received": True}, status=200)

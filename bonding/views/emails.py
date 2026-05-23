from rest_framework.views import APIView
from django.shortcuts import redirect
from django.conf import settings
from bonding.models import User, VerificationToken


class VerifyEmailView(APIView):
    permission_classes = []

    def _redirect_to_frontend(self, status):
        base_url = settings.FRONTEND_URL.rstrip("/")
        return redirect(f"{base_url}/?email_verification={status}")

    def get(self, request, user_id, token):
        try:
            user = User.objects.get(id=user_id)
            verification_token = VerificationToken.objects.get(user=user, token=token)

            if not verification_token.is_valid():
                return self._redirect_to_frontend("expired")

            user.is_active = True
            user.save(update_fields=["is_active"])
            verification_token.delete()

            return self._redirect_to_frontend("success")
        except (User.DoesNotExist, VerificationToken.DoesNotExist):
            return self._redirect_to_frontend("failed")


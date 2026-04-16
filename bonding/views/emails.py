from rest_framework.views import APIView
from django.shortcuts import redirect
from bonding.models import User, VerificationToken


class VerifyEmailView(APIView):
    permission_classes = []

    def get(self, request, user_id, token):
        try:
            user = User.objects.get(id=user_id)
            verification_token = VerificationToken.objects.get(user=user, token=token)

            if not verification_token.is_valid():
                return redirect("http://seu-frontend.com/verificacao-expirada")

            user.is_active = True
            user.save()
            verification_token.delete()

            return redirect("http://seu-frontend.com/verificacao-sucesso")
        except (User.DoesNotExist, VerificationToken.DoesNotExist):
            return redirect("http://seu-frontend.com/verificacao-falha")


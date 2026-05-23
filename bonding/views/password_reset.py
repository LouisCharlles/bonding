from datetime import timedelta
import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from ..models import PasswordResetToken

User = get_user_model()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "As senhas não correspondem."}
            )
        return attrs


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower().strip()
        user = User.objects.filter(email=email).first()
        if user:
            reset_token, _ = PasswordResetToken.objects.update_or_create(
                user=user,
                defaults={
                    "token": uuid.uuid4(),
                    "expires_at": timezone.now() + timedelta(minutes=30),
                },
            )

            reset_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/"
                f"{user.id}/{reset_token.token}"
            )

            try:
                send_mail(
                    "Redefinição de senha - Bonding",
                    (
                        "Recebemos um pedido para redefinir sua senha.\n\n"
                        f"Acesse o link para continuar: {reset_url}\n\n"
                        "Se você não pediu essa alteração, ignore este e-mail."
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as exc:
                logger.error(
                    "Password reset email failed for user %s: %s",
                    user.id,
                    exc,
                    exc_info=True,
                )

        return Response(
            {
                "detail": (
                    "Se existir uma conta com esse e-mail, enviaremos um link "
                    "de redefinição de senha."
                )
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, user_id, token):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=user_id)
            reset_token = PasswordResetToken.objects.get(user=user, token=token)
        except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
            return Response(
                {"detail": "Link de redefinição inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reset_token.is_valid():
            reset_token.delete()
            return Response(
                {"detail": "Link de redefinição expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        reset_token.delete()

        return Response(
            {"detail": "Senha redefinida com sucesso."},
            status=status.HTTP_200_OK,
        )

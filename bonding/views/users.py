from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bonding.serializers import RegisterSerializer, UserSummarySerializer
from bonding.services.presence import touch_user_presence

User = get_user_model()


class RegisterUserView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        touch_user_presence(request.user, active=True)
        return Response(UserSummarySerializer(request.user).data, status=status.HTTP_200_OK)


class PresenceHeartbeatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        active = bool(request.data.get("active", True))
        profile = touch_user_presence(request.user, active=active)
        return Response(
            {
                "active": active,
                "is_online": getattr(profile, "is_online", False),
                "last_seen": getattr(profile, "last_seen", None),
            },
            status=status.HTTP_200_OK,
        )

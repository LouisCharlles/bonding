from django.conf import settings
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from ..auth_cookies import clear_auth_cookies, set_access_cookie, set_refresh_cookie
from ..serializers import CustomTokenObtainPairSerializer


class CookieBackedTokenRefreshSerializer(TokenRefreshSerializer):
    refresh = serializers.CharField(required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        refresh_token = attrs.get("refresh")
        if not refresh_token and request is not None:
            refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh_token:
            raise serializers.ValidationError({"detail": "Refresh token ausente."})
        attrs["refresh"] = refresh_token
        return super().validate(attrs)


class CustomTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CustomTokenObtainPairSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        access_token = payload["access"]
        refresh_token = payload["refresh"]
        user = payload["user"]

        response = Response(
            {
                "access": access_token,
                "user": user,
            },
            status=status.HTTP_200_OK,
        )
        set_access_cookie(response, access_token)
        set_refresh_cookie(response, refresh_token)
        return response


class CustomTokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CookieBackedTokenRefreshSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        access_token = payload["access"]

        response = Response({"access": access_token}, status=status.HTTP_200_OK)
        set_access_cookie(response, access_token)

        next_refresh_token = payload.get("refresh")
        if next_refresh_token:
            set_refresh_cookie(response, next_refresh_token)
        return response


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response

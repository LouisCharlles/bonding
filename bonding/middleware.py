from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import UntypedToken

from .models import User


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    def _get_cookie_value(self, scope, name):
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()
        if not cookie_header:
            return None

        for part in cookie_header.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        token = self._get_cookie_value(scope, settings.AUTH_ACCESS_COOKIE_NAME)

        if token:
            try:
                validated_token = UntypedToken(token)
                user_id = validated_token.get(api_settings.USER_ID_CLAIM)
                if user_id is not None:
                    scope["user"] = await get_user(user_id)
            except (InvalidToken, TokenError):
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

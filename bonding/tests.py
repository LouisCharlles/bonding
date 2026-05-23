import json
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import UntypedToken

from bonding.middleware import JwtAuthMiddleware
from bonding.models import (
    Conversation,
    Message,
    Profile,
    ProfileVerificationAttempt,
    User,
    VerificationSelfie,
)
from bonding.storage import SupabaseStorage


@override_settings(
    AUTH_COOKIE_SECURE=False,
    AUTH_COOKIE_DOMAIN="",
    AUTH_COOKIE_SAMESITE="Lax",
    BACKEND_URL="http://testserver",
    SECURE_SSL_REDIRECT=False,
)
class AuthenticationCookieTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(email="alice@example.com", password=self.password)
        Profile.objects.create(
            user=self.user,
            name="Alice",
            age=24,
            gender=Profile.GENDER_OTHER,
            sexual_orientation=Profile.ORIENTATION_OTHER,
            course="Computacao",
        )

    def test_login_sets_access_and_refresh_cookies(self):
        response = self.client.post(
            "/api/token/",
            data=json.dumps({"email": self.user.email, "password": self.password}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("user", response.json())
        self.assertIn(settings.AUTH_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[settings.AUTH_ACCESS_COOKIE_NAME]["httponly"])
        self.assertTrue(response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["httponly"])

    def test_refresh_uses_refresh_cookie(self):
        login_response = self.client.post(
            "/api/token/",
            data=json.dumps({"email": self.user.email, "password": self.password}),
            content_type="application/json",
        )
        refresh_cookie = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
        self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = refresh_cookie

        response = self.client.post(
            "/api/token/refresh/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn(settings.AUTH_ACCESS_COOKIE_NAME, response.cookies)

    def test_logout_clears_auth_cookies(self):
        response = self.client.post("/api/token/logout/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[settings.AUTH_ACCESS_COOKIE_NAME].value, "")
        self.assertEqual(response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value, "")


class EncryptedFieldTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="one@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="two@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user,
                name=f"User {index}",
                age=20 + index,
                gender=Profile.GENDER_OTHER,
                sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)

    def test_message_provider_payload_is_not_stored_as_plain_json(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="oi",
            provider_payload={"secret": "maps://hidden"},
        )

        refreshed = Message.objects.get(pk=message.pk)
        self.assertEqual(refreshed.provider_payload, {"secret": "maps://hidden"})

        with connection.cursor() as cursor:
            cursor.execute("SELECT provider_payload FROM bonding_message WHERE id = %s", [message.id])
            raw_value = cursor.fetchone()[0]

        raw_bytes = bytes(raw_value) if isinstance(raw_value, memoryview) else raw_value
        self.assertIsInstance(raw_bytes, (bytes, bytearray))
        self.assertNotIn(b"maps://hidden", raw_bytes)

    def test_verification_attempt_payload_is_not_stored_as_plain_json(self):
        attempt = ProfileVerificationAttempt.objects.create(
            profile=self.user1.profile,
            provider_payload={"score_source": "rekognition"},
        )
        VerificationSelfie.objects.create(attempt=attempt, image="verification_selfies/test.jpg")

        refreshed = ProfileVerificationAttempt.objects.get(pk=attempt.pk)
        self.assertEqual(refreshed.provider_payload, {"score_source": "rekognition"})

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT provider_payload FROM bonding_profileverificationattempt WHERE id = %s",
                [attempt.id],
            )
            raw_value = cursor.fetchone()[0]

        raw_bytes = bytes(raw_value) if isinstance(raw_value, memoryview) else raw_value
        self.assertIsInstance(raw_bytes, (bytes, bytearray))
        self.assertNotIn(b"rekognition", raw_bytes)


@override_settings(AUTH_ACCESS_COOKIE_NAME="bonding_access", SECURE_SSL_REDIRECT=False)
class JwtAuthMiddlewareTests(TestCase):
    def test_middleware_extracts_cookie_token_that_can_be_validated(self):
        User.objects.create_user(email="cookie@example.com", password="StrongPass123!")
        token_response = self.client.post(
            "/api/token/",
            data=json.dumps({"email": "cookie@example.com", "password": "StrongPass123!"}),
            content_type="application/json",
        )
        access_token = token_response.cookies["bonding_access"].value

        middleware = JwtAuthMiddleware(lambda scope, receive, send: None)
        token_from_cookie = middleware._get_cookie_value({
            "type": "websocket",
            "headers": [(b"cookie", f"bonding_access={access_token}".encode())],
        }, "bonding_access")

        validated_token = UntypedToken(token_from_cookie)
        self.assertEqual(str(validated_token), str(UntypedToken(access_token)))
        self.assertIsNotNone(validated_token.get(api_settings.USER_ID_CLAIM))


class SupabaseStorageTests(TestCase):
    def test_signed_url_response_without_storage_prefix_is_normalized(self):
        storage = SupabaseStorage(
            base_url="https://example.supabase.co",
            bucket="profile-gallery",
            service_role_key="secret",
        )

        signed_payload = BytesIO(
            json.dumps(
                {
                    "signedURL": "/object/sign/profile-gallery/photos/avatar.jpg?token=abc123",
                }
            ).encode("utf-8")
        )
        signed_payload.__enter__ = lambda self=signed_payload: self
        signed_payload.__exit__ = lambda exc_type, exc, tb: False

        with patch.object(storage, "_request", return_value=signed_payload):
            url = storage.url("photos/avatar.jpg")

        self.assertEqual(
            url,
            "https://example.supabase.co/storage/v1/object/sign/profile-gallery/photos/avatar.jpg?token=abc123",
        )

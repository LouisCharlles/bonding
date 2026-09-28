import json
import os
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import UntypedToken

from bonding.middleware import JwtAuthMiddleware
from bonding.models import (
    ConsentRecord,
    Conversation,
    ConversationStageSnapshot,
    DateSuggestionFeedback,
    LegalDocumentVersion,
    Match,
    Message,
    PremiumPlan,
    Profile,
    ProfileVerificationAttempt,
    Subscription,
    User,
    UserLocationPing,
    VerificationSelfie,
)
from bonding.services.consent import record_consent, verify_chain_integrity
from bonding.storage import SupabaseStorage
from bonding.tasks import check_date_intent_task


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


@override_settings(GEMINI_API_KEY="test-key")
class AnalyzeConversationStageTests(TestCase):
    def test_missing_api_key_returns_fallback_without_calling_gemini(self):
        from bonding.services.gemini import analyze_conversation_stage

        with override_settings(GEMINI_API_KEY=""):
            with patch("bonding.services.gemini.genai") as mock_genai:
                result = analyze_conversation_stage([{"label": "User A", "content": "oi"}])

        mock_genai.configure.assert_not_called()
        self.assertEqual(result["stage"], "quebra_gelo")
        self.assertEqual(result["interests"], [])

    def test_valid_response_is_parsed_and_unknown_interests_are_filtered(self):
        from bonding.services.gemini import analyze_conversation_stage

        mock_response = type("Resp", (), {"text": json.dumps({
            "stage": "pronto_para_role",
            "stage_confidence": 92,
            "interests": ["food", "invalido"],
            "tipo_role": "gastronomico",
        })})()

        with patch("bonding.services.gemini.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            result = analyze_conversation_stage([{"label": "User A", "content": "bora comer sushi hoje?"}])

        self.assertEqual(result["stage"], "pronto_para_role")
        self.assertEqual(result["interests"], ["food"])

    def test_exception_falls_back_to_neutral_result(self):
        from bonding.services.gemini import analyze_conversation_stage

        with patch("bonding.services.gemini.genai") as mock_genai:
            mock_genai.GenerativeModel.side_effect = RuntimeError("boom")
            result = analyze_conversation_stage([{"label": "User A", "content": "oi"}])

        self.assertEqual(result["stage"], "quebra_gelo")
        self.assertEqual(result["stage_confidence"], 0)


class CheckDateIntentTaskTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="a@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="b@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        for i in range(10):
            Message.objects.create(
                conversation=self.conversation,
                sender=self.user1 if i % 2 == 0 else self.user2,
                content=f"mensagem {i}",
            )

    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_snapshot_is_persisted_even_when_intent_is_none(self, mock_intent, mock_stage):
        mock_intent.return_value = {"intent": "NONE", "confidence": 0, "entities": {}}
        mock_stage.return_value = {
            "stage": "rapport", "stage_confidence": 55, "interests": ["coffee"], "tipo_role": None,
        }

        with patch("bonding.services.realtime.publish_group_event") as mock_publish:
            check_date_intent_task.run(self.conversation.id)

        mock_publish.assert_not_called()
        snapshot = ConversationStageSnapshot.objects.get(conversation_id=self.conversation.id)
        self.assertEqual(snapshot.stage, "rapport")
        self.assertEqual(snapshot.interests, ["coffee"])

    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_query_falls_back_to_interest_label_when_no_amenity(self, mock_intent, mock_stage, mock_places):
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": ["bars"], "tipo_role": "bar",
        }
        mock_places.return_value = []

        with patch("bonding.services.realtime.publish_group_event"):
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_not_called()  # no location ping was created, so search is skipped entirely

    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_publishes_stage_fields_in_ws_payload(self, mock_intent, mock_stage, mock_places):
        from bonding.models import UserLocationPing

        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.3)
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": ["bars"], "tipo_role": "bar",
        }
        mock_places.return_value = []

        with patch("bonding.services.realtime.publish_group_event") as mock_publish:
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_called_once()
        self.assertEqual(mock_places.call_args.kwargs["query"], "Bares")
        payload = mock_publish.call_args.args[1]
        self.assertEqual(payload["data"]["stage"], "pronto_para_role")
        self.assertEqual(payload["data"]["interests"], ["bars"])

    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_cooldown_active_skips_pipeline_and_reuses_cache(self, mock_intent, mock_stage, mock_places, mock_rerank):
        cached = [{"name": "Lugar em cache", "distance_km": 1.0, "latitude": -2.53, "longitude": -44.30}]
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation,
            last_suggested_at=timezone.now(),
            last_suggested_message_count=5,
            cached_suggestions=cached,
        )
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }

        with patch("bonding.services.realtime.publish_group_event") as mock_publish:
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_not_called()
        mock_rerank.assert_not_called()
        payload = mock_publish.call_args.args[1]
        self.assertTrue(payload["data"]["cache_hit"])
        self.assertEqual(payload["data"]["suggestions"], cached)

    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_cooldown_expired_by_time_recomputes(self, mock_intent, mock_stage, mock_places, mock_rerank):
        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.30)
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation,
            last_suggested_at=timezone.now() - timedelta(hours=2),
            last_suggested_message_count=5,
            cached_suggestions=[],
        )
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }
        mock_places.return_value = []
        mock_rerank.return_value = ([], "deterministic_fallback")

        with patch("bonding.services.realtime.publish_group_event"):
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_called_once()
        mock_rerank.assert_called_once()

    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_cooldown_expired_by_message_count_recomputes(self, mock_intent, mock_stage, mock_places, mock_rerank):
        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.30)
        for i in range(10, 15):
            Message.objects.create(
                conversation=self.conversation,
                sender=self.user1 if i % 2 == 0 else self.user2,
                content=f"mensagem {i}",
            )
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation,
            last_suggested_at=timezone.now(),
            last_suggested_message_count=0,
            cached_suggestions=[],
        )
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }
        mock_places.return_value = []
        mock_rerank.return_value = ([], "deterministic_fallback")

        with patch("bonding.services.realtime.publish_group_event"):
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_called_once()
        mock_rerank.assert_called_once()

    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_shown_feedback_rows_created_with_round_id(self, mock_intent, mock_stage, mock_places, mock_rerank):
        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.30)
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }
        mock_places.return_value = [
            {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
             "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5, "deterministic_score": 0.8},
        ]
        mock_rerank.return_value = (
            [
                {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
                 "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5,
                 "deterministic_score": 0.8, "llm_score": 95, "llm_rank": 1, "llm_reason": "Combina"},
            ],
            "llm",
        )

        with patch("bonding.services.realtime.publish_group_event"):
            check_date_intent_task.run(self.conversation.id)

        feedback_rows = DateSuggestionFeedback.objects.filter(conversation=self.conversation)
        self.assertEqual(feedback_rows.count(), 1)
        row = feedback_rows.first()
        self.assertEqual(row.place_name, "Lugar 1")
        self.assertEqual(row.llm_score, 95)
        self.assertEqual(row.deterministic_score, 0.8)
        self.assertEqual(row.source, DateSuggestionFeedback.SOURCE_AUTOMATIC)

    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_cross_round_dedup_excludes_recently_shown_unused_place(
        self, mock_intent, mock_stage, mock_places, mock_rerank
    ):
        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.30)
        DateSuggestionFeedback.objects.create(
            conversation=self.conversation,
            place_name="Bar Central",
            place_latitude=-2.5310,
            place_longitude=-44.3010,
            round_id="11111111-1111-1111-1111-111111111111",
        )
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }
        mock_places.return_value = [
            {"name": "Bar Central", "distance_km": 1.0, "latitude": -2.5310, "longitude": -44.3010,
             "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5, "deterministic_score": 0.8},
            {"name": "Novo Lugar", "distance_km": 1.2, "latitude": -2.5320, "longitude": -44.3020,
             "vicinity": "Rua 2", "rating": None, "metadata_completeness_score": 0.5, "deterministic_score": 0.7},
        ]
        mock_rerank.return_value = ([], "deterministic_fallback")

        with patch("bonding.services.realtime.publish_group_event"):
            check_date_intent_task.run(self.conversation.id)

        mock_rerank.assert_called_once()
        candidates_passed = mock_rerank.call_args.args[0]
        self.assertEqual([c["name"] for c in candidates_passed], ["Novo Lugar"])

    @override_settings(DATE_SUGGESTION_CONFIDENCE_THRESHOLD=95)
    @patch("bonding.services.date_ranking.rerank_suggestions_with_llm")
    @patch("bonding.services.external_integrations.get_overpass_suggestions")
    @patch("bonding.services.gemini.analyze_conversation_stage")
    @patch("bonding.services.gemini.analyze_chat_intent")
    def test_confidence_threshold_setting_is_respected(self, mock_intent, mock_stage, mock_places, mock_rerank):
        mock_intent.return_value = {"intent": "SUGGEST_DATE", "confidence": 90, "entities": {}}
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90, "interests": [], "tipo_role": None,
        }

        with patch("bonding.services.realtime.publish_group_event") as mock_publish:
            check_date_intent_task.run(self.conversation.id)

        mock_places.assert_not_called()
        mock_rerank.assert_not_called()
        mock_publish.assert_not_called()


class ConversationDateReadinessViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(email="c@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="d@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        self.client.force_authenticate(self.user1)
        self.url = f"/conversations/{self.conversation.id}/date-readiness/"

    def test_no_snapshot_falls_back_to_heuristic(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "heuristic")

    @override_settings(GEMINI_API_KEY="test-key")
    def test_snapshot_with_api_key_returns_gemini_source(self):
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation,
            stage="interesse_mutuo",
            stage_confidence=80,
            interests=["food"],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["source"], "gemini")
        self.assertTrue(body["ready"])
        self.assertEqual(body["stage"], "interesse_mutuo")

    @override_settings(GEMINI_API_KEY="")
    def test_snapshot_without_api_key_still_falls_back_to_heuristic(self):
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation, stage="pronto_para_role", stage_confidence=90,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.json()["source"], "heuristic")


class MaybeTriggerIntentAnalysisTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="e@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="f@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)

    @patch("bonding.tasks.check_date_intent_task.delay")
    def test_triggers_only_on_every_tenth_text_message(self, mock_delay):
        from bonding.views.messages import MessageViewSet

        viewset = MessageViewSet()
        for i in range(1, 12):
            message = Message.objects.create(
                conversation=self.conversation,
                sender=self.user1 if i % 2 else self.user2,
                content=f"mensagem {i}",
            )
            viewset._maybe_trigger_intent_analysis(message)

        mock_delay.assert_called_once_with(self.conversation.id)


class ExternalIntegrationsRankingTests(TestCase):
    def test_metadata_completeness_score_full_tags(self):
        from bonding.services.external_integrations import compute_metadata_completeness_score

        score = compute_metadata_completeness_score({
            "opening_hours": "Mo-Su 10:00-22:00",
            "phone": "+55 98 99999-0000",
            "website": "https://example.com",
            "addr:housenumber": "100",
            "addr:street": "Rua Um",
        })
        self.assertEqual(score, 1.0)

    def test_metadata_completeness_score_minimal_tags(self):
        from bonding.services.external_integrations import compute_metadata_completeness_score

        self.assertEqual(compute_metadata_completeness_score({}), 0.0)

    def test_deterministic_prefilter_score_prefers_closer_and_more_complete(self):
        from bonding.services.external_integrations import deterministic_prefilter_score

        close_complete = {"distance_km": 0.5, "metadata_completeness_score": 1.0}
        far_incomplete = {"distance_km": 4.5, "metadata_completeness_score": 0.0}
        deterministic_prefilter_score(close_complete, max_radius_km=5)
        deterministic_prefilter_score(far_incomplete, max_radius_km=5)

        self.assertGreater(close_complete["deterministic_score"], far_incomplete["deterministic_score"])

    def test_overpass_category_search_dedupes_and_sorts_by_score(self):
        from bonding.services.external_integrations import _overpass_category_search

        response = {
            "elements": [
                {"type": "node", "id": 1, "lat": -2.531, "lon": -44.302, "tags": {"name": "Duplicado"}},
                {"type": "node", "id": 1, "lat": -2.531, "lon": -44.302, "tags": {"name": "Duplicado"}},
                {
                    "type": "node", "id": 2, "lat": -2.530, "lon": -44.300,
                    "tags": {
                        "name": "Completo", "opening_hours": "Mo-Su 10:00-22:00",
                        "phone": "123", "website": "https://x.com",
                        "addr:housenumber": "1", "addr:street": "Rua X",
                    },
                },
            ],
        }
        with patch("bonding.services.external_integrations._overpass_request", return_value=response):
            results = _overpass_category_search(-2.53, -44.30, 5000, ["amenity=restaurant"])

        names = [r["name"] for r in results]
        self.assertEqual(names.count("Duplicado"), 1)
        self.assertEqual(results[0]["name"], "Completo")


class RerankSuggestionsWithLlmTests(TestCase):
    def setUp(self):
        self.candidates = [
            {"name": "Lugar A", "distance_km": 1.0, "vicinity": "Rua A", "latitude": -2.53, "longitude": -44.30,
             "metadata_completeness_score": 0.5, "deterministic_score": 0.7},
            {"name": "Lugar B", "distance_km": 2.0, "vicinity": "Rua B", "latitude": -2.54, "longitude": -44.31,
             "metadata_completeness_score": 0.25, "deterministic_score": 0.4},
        ]

    @override_settings(GEMINI_API_KEY="")
    def test_no_api_key_falls_back_to_deterministic(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        mock_genai.configure.assert_not_called()
        self.assertEqual(source, "deterministic_fallback")
        self.assertEqual([p["name"] for p in ranked], ["Lugar A", "Lugar B"])
        self.assertIsNone(ranked[0]["llm_score"])
        self.assertEqual(ranked[0]["llm_rank"], 1)

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.services.date_ranking.random.shuffle", new=lambda seq: None)
    def test_llm_success_reorders_and_scores(self):
        from bonding.services.date_ranking import RERANK_PROMPT_VERSION, rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [
                {"index": 1, "score": 88, "reason": "Combina com o clima da conversa"},
                {"index": 0, "score": 60, "reason": "Também é uma opção"},
            ]
        })})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {"stage": "pronto_para_role"}, top_n=5)

        self.assertEqual(source, "llm")
        self.assertEqual([p["name"] for p in ranked], ["Lugar B", "Lugar A"])
        self.assertEqual(ranked[0]["llm_score"], 88)
        self.assertEqual(ranked[0]["llm_rank"], 1)
        self.assertEqual(ranked[0]["llm_reason"], "Combina com o clima da conversa")
        self.assertEqual(ranked[0]["prompt_version"], RERANK_PROMPT_VERSION)
        # unshuffled presentation order: prompt index N == ordered[N], so
        # "Lugar B" (ordered[1]) was shown at prompt position 2, "Lugar A"
        # (ordered[0]) at prompt position 1.
        self.assertEqual(ranked[0]["prompt_position"], 2)
        self.assertEqual(ranked[1]["prompt_position"], 1)
        self.assertEqual(ranked[0]["invalid_index_count"], 0)

    @override_settings(GEMINI_API_KEY="test-key")
    def test_position_shuffle_maps_prompt_index_back_to_correct_candidate(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [{"index": 0, "score": 90, "reason": "Melhor opcao"}]
        })})()

        with patch("bonding.services.date_ranking.genai") as mock_genai, \
                patch("bonding.services.date_ranking.random.shuffle", side_effect=lambda seq: seq.reverse()):
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        # ordered = [Lugar A (0.7), Lugar B (0.4)]; presentation_order reversed
        # to [1, 0] -> prompt index 0 refers to original index 1 (Lugar B).
        self.assertEqual(source, "llm")
        self.assertEqual(ranked[0]["name"], "Lugar B")
        self.assertEqual(ranked[0]["prompt_position"], 1)

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.services.date_ranking.random.shuffle", new=lambda seq: None)
    def test_invalid_indices_are_counted_without_leaking_into_output(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [
                {"index": 99, "score": 10, "reason": "fora do range"},
                {"index": 0, "score": 10, "reason": "duplicado"},
                {"index": 0, "score": 10, "reason": "duplicado de novo"},
                {"index": 1, "score": 70, "reason": "valido"},
            ]
        })})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        self.assertEqual(source, "llm")
        self.assertEqual(len(ranked), 2)
        self.assertEqual({p["invalid_index_count"] for p in ranked}, {2})

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.services.date_ranking.random.shuffle", new=lambda seq: None)
    def test_all_invalid_indices_falls_back_with_count(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [
                {"index": 99, "score": 10, "reason": "fora do range"},
                {"index": -1, "score": 10, "reason": "negativo"},
            ]
        })})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        self.assertEqual(source, "deterministic_fallback")
        self.assertEqual({p["invalid_index_count"] for p in ranked}, {2})

    @override_settings(GEMINI_API_KEY="")
    def test_fallback_places_have_null_prompt_metadata(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        mock_genai.configure.assert_not_called()
        self.assertEqual(source, "deterministic_fallback")
        for place in ranked:
            self.assertIsNone(place["prompt_version"])
            self.assertIsNone(place["prompt_position"])
            self.assertIsNone(place["invalid_index_count"])

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.services.date_ranking.random.shuffle", new=lambda seq: None)
    def test_custom_prompt_template_is_used_when_provided(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [{"index": 0, "score": 90, "reason": "ok"}]
        })})()
        custom_template = "TEMPLATE-MARCADOR {candidates_block} {top_n}"

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(
                self.candidates, {}, top_n=5,
                prompt_template=custom_template, prompt_version="custom_v1",
            )
            sent_prompt = mock_genai.GenerativeModel.return_value.generate_content.call_args[0][0]

        self.assertEqual(source, "llm")
        self.assertIn("TEMPLATE-MARCADOR", sent_prompt)
        self.assertEqual(ranked[0]["prompt_version"], "custom_v1")

    @override_settings(GEMINI_API_KEY="test-key")
    def test_llm_invalid_json_falls_back(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": "not json"})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        self.assertEqual(source, "deterministic_fallback")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.services.date_ranking.random.shuffle", new=lambda seq: None)
    def test_llm_out_of_range_index_falls_back(self):
        from bonding.services.date_ranking import rerank_suggestions_with_llm

        mock_response = type("Resp", (), {"text": json.dumps({
            "ranking": [{"index": 99, "score": 50, "reason": "?"}]
        })})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            ranked, source = rerank_suggestions_with_llm(self.candidates, {}, top_n=5)

        self.assertEqual(source, "deterministic_fallback")


class RankDeterministicOnlyTests(TestCase):
    def setUp(self):
        self.candidates = [
            {"name": "Lugar A", "distance_km": 1.0, "vicinity": "Rua A", "latitude": -2.53, "longitude": -44.30,
             "metadata_completeness_score": 0.5, "deterministic_score": 0.7},
            {"name": "Lugar B", "distance_km": 2.0, "vicinity": "Rua B", "latitude": -2.54, "longitude": -44.31,
             "metadata_completeness_score": 0.25, "deterministic_score": 0.4},
        ]

    def test_matches_deterministic_fallback_ordering(self):
        from bonding.services.date_ranking import _deterministic_fallback, rank_deterministic_only

        ordered = sorted(self.candidates, key=lambda c: c.get("deterministic_score") or 0, reverse=True)
        expected, _source = _deterministic_fallback(ordered, top_n=5)

        result = rank_deterministic_only(self.candidates, top_n=5)

        self.assertEqual([p["name"] for p in result], [p["name"] for p in expected])
        self.assertEqual([p["llm_rank"] for p in result], [p["llm_rank"] for p in expected])
        self.assertTrue(all(p["llm_score"] is None for p in result))


class MatchDateSuggestionsViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(email="i@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="j@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        self.match = Match.objects.create(user1=self.user1, user2=self.user2, conversation=self.conversation)
        UserLocationPing.objects.create(user=self.user1, latitude=-2.53, longitude=-44.30)
        self.client.force_authenticate(self.user1)
        self.url = f"/matches/{self.match.id}/date-suggestions/"

    @patch("bonding.views.match_features.rerank_suggestions_with_llm")
    @patch("bonding.views.match_features.get_overpass_suggestions")
    def test_returns_ranked_places_with_scores(self, mock_places, mock_rerank):
        mock_places.return_value = [
            {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
             "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5, "deterministic_score": 0.8},
        ]
        mock_rerank.return_value = (
            [
                {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
                 "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5,
                 "deterministic_score": 0.8, "llm_score": 77, "llm_rank": 1, "llm_reason": "Combina"},
            ],
            "llm",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body[0]["deterministic_score"], 0.8)
        self.assertEqual(body[0]["llm_score"], 77)
        feedback = DateSuggestionFeedback.objects.filter(match=self.match)
        self.assertEqual(feedback.count(), 1)
        self.assertEqual(feedback.first().source, DateSuggestionFeedback.SOURCE_MANUAL)

    @patch("bonding.views.match_features.rerank_suggestions_with_llm")
    @patch("bonding.views.match_features.get_overpass_suggestions")
    def test_ignores_cooldown_always_fresh(self, mock_places, mock_rerank):
        ConversationStageSnapshot.objects.create(
            conversation=self.conversation,
            last_suggested_at=timezone.now(),
            last_suggested_message_count=0,
            cached_suggestions=[{"name": "Cache antigo", "distance_km": 1.0, "latitude": -2.53, "longitude": -44.30}],
        )
        mock_places.return_value = []
        mock_rerank.return_value = ([], "deterministic_fallback")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        mock_places.assert_called_once()
        mock_rerank.assert_called_once()

    @patch("bonding.views.match_features.rerank_suggestions_with_llm")
    @patch("bonding.views.match_features.get_overpass_suggestions")
    def test_metadata_includes_prompt_version_position_and_invalid_count(self, mock_places, mock_rerank):
        mock_places.return_value = [
            {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
             "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5, "deterministic_score": 0.8},
        ]
        mock_rerank.return_value = (
            [
                {"name": "Lugar 1", "distance_km": 1.0, "latitude": -2.531, "longitude": -44.301,
                 "vicinity": "Rua 1", "rating": None, "metadata_completeness_score": 0.5,
                 "deterministic_score": 0.8, "llm_score": 77, "llm_rank": 1, "llm_reason": "Combina",
                 "prompt_version": "rerank_v1", "prompt_position": 1, "invalid_index_count": 0},
            ],
            "llm",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        feedback = DateSuggestionFeedback.objects.filter(match=self.match).first()
        self.assertEqual(feedback.metadata["prompt_version"], "rerank_v1")
        self.assertEqual(feedback.metadata["prompt_position"], 1)
        self.assertEqual(feedback.metadata["invalid_index_count"], 0)


class MarkSuggestionUsedTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="k@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="l@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        self.feedback = DateSuggestionFeedback.objects.create(
            conversation=self.conversation,
            place_name="Bar Central",
            place_latitude=-2.5300,
            place_longitude=-44.3000,
            round_id="11111111-1111-1111-1111-111111111111",
        )

    def test_date_suggestion_message_marks_matching_feedback_used(self):
        from bonding.views.messages import MessageViewSet

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=Message.TYPE_DATE_SUGGESTION,
            content="Bar Central",
            provider_payload={"name": "Bar Central", "latitude": -2.5300, "longitude": -44.3000},
        )
        MessageViewSet()._maybe_mark_suggestion_used(message)

        self.feedback.refresh_from_db()
        self.assertIsNotNone(self.feedback.used_at)

    def test_non_matching_payload_does_not_mark_anything(self):
        from bonding.views.messages import MessageViewSet

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=Message.TYPE_DATE_SUGGESTION,
            content="Outro lugar",
            provider_payload={"name": "Outro Lugar", "latitude": -3.0, "longitude": -45.0},
        )
        MessageViewSet()._maybe_mark_suggestion_used(message)

        self.feedback.refresh_from_db()
        self.assertIsNone(self.feedback.used_at)

    @patch("bonding.services.date_ranking.mark_suggestion_used")
    def test_text_message_does_not_attempt_marking(self, mock_mark):
        from bonding.views.messages import MessageViewSet

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=Message.TYPE_TEXT,
            content="oi",
        )
        MessageViewSet()._maybe_mark_suggestion_used(message)

        mock_mark.assert_not_called()


class DateExperimentVariantsTests(TestCase):
    def setUp(self):
        self.candidates = [
            {"name": "Lugar A", "distance_km": 1.0, "vicinity": "Rua A", "latitude": -2.53, "longitude": -44.30,
             "metadata_completeness_score": 0.5, "deterministic_score": 0.7},
        ]

    @override_settings(GEMINI_API_KEY="")
    def test_run_ai_pure_without_api_key_returns_empty(self):
        from bonding.services.date_experiment_variants import run_ai_pure

        result = run_ai_pure({}, "São Luís - MA", top_n=5)

        self.assertEqual(result, [])

    @override_settings(GEMINI_API_KEY="test-key")
    def test_run_ai_pure_parses_suggestions(self):
        from bonding.services.date_experiment_variants import AI_PURE_PROMPT_VERSION, run_ai_pure

        mock_response = type("Resp", (), {"text": json.dumps({
            "suggestions": [
                {"name": "Restaurante Ficticio", "city": "São Luís", "estimated_address": None, "reason": "Combina"},
            ]
        })})()

        with patch("bonding.services.date_experiment_variants.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            result = run_ai_pure({"stage": "pronto_para_role"}, "São Luís - MA", top_n=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Restaurante Ficticio")
        self.assertEqual(result[0]["declared_city"], "São Luís")
        self.assertEqual(result[0]["prompt_version"], AI_PURE_PROMPT_VERSION)

    def test_run_deterministic_pure_matches_rank_deterministic_only(self):
        from bonding.services.date_experiment_variants import run_deterministic_pure
        from bonding.services.date_ranking import rank_deterministic_only

        result = run_deterministic_pure(self.candidates, top_n=5)
        expected = rank_deterministic_only(self.candidates, top_n=5)

        self.assertEqual([p["name"] for p in result], [p["name"] for p in expected])

    @override_settings(GEMINI_API_KEY="test-key")
    def test_hybrid_control_simple_prompt_omits_full_rubric_text(self):
        from bonding.services.date_experiment_variants import run_hybrid_control_simple_prompt

        mock_response = type("Resp", (), {"text": json.dumps({"ranking": []})})()

        with patch("bonding.services.date_ranking.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
            run_hybrid_control_simple_prompt(self.candidates, {}, top_n=5)
            sent_prompt = mock_genai.GenerativeModel.return_value.generate_content.call_args[0][0]

        self.assertNotIn("REORDENAR os candidatos pela relevância semântica", sent_prompt)


class GenerateDateExperimentDatasetCommandTests(TestCase):
    def test_command_is_idempotent(self):
        call_command("generate_date_experiment_dataset")
        first_count = User.objects.filter(email__endswith="@tcc-experiment.bonding.local").count()

        call_command("generate_date_experiment_dataset")
        second_count = User.objects.filter(email__endswith="@tcc-experiment.bonding.local").count()

        self.assertEqual(first_count, second_count)
        self.assertGreater(first_count, 0)

    def test_cleanup_removes_all_experiment_data(self):
        call_command("generate_date_experiment_dataset")
        self.assertTrue(User.objects.filter(email__endswith="@tcc-experiment.bonding.local").exists())

        call_command("generate_date_experiment_dataset", "--cleanup")

        self.assertFalse(User.objects.filter(email__endswith="@tcc-experiment.bonding.local").exists())
        self.assertFalse(Conversation.objects.filter(
            user1__email__endswith="@tcc-experiment.bonding.local",
        ).exists())


class RunDateExperimentCommandTests(TestCase):
    def setUp(self):
        call_command("generate_date_experiment_dataset")

    @override_settings(GEMINI_API_KEY="test-key")
    @patch("bonding.management.commands.run_date_experiment.run_hybrid_control_simple_prompt")
    @patch("bonding.management.commands.run_date_experiment.run_hybrid_full")
    @patch("bonding.management.commands.run_date_experiment.run_deterministic_pure")
    @patch("bonding.management.commands.run_date_experiment.run_ai_pure")
    @patch("bonding.management.commands.run_date_experiment.get_overpass_suggestions")
    @patch("bonding.management.commands.run_date_experiment.analyze_conversation_stage")
    def test_persists_four_variants_per_conversation_with_shared_run_id(
        self, mock_stage, mock_overpass, mock_ai_pure, mock_det, mock_hybrid, mock_control,
    ):
        mock_stage.return_value = {
            "stage": "pronto_para_role", "stage_confidence": 90,
            "interests": ["food"], "tipo_role": "gastronomico",
        }
        candidate = {
            "name": "Lugar X", "distance_km": 1.0, "latitude": -2.53, "longitude": -44.30,
            "vicinity": "Rua X", "metadata_completeness_score": 0.5, "deterministic_score": 0.7,
        }
        mock_overpass.return_value = [candidate]
        mock_ai_pure.return_value = [{
            "name": "Lugar Livre", "declared_city": "São Luís", "llm_rank": 1, "llm_score": None,
            "llm_reason": None, "prompt_version": "ai_pure_v1", "prompt_position": None,
            "invalid_index_count": None,
        }]
        mock_det.return_value = [dict(
            candidate, llm_score=None, llm_rank=1, llm_reason=None,
            prompt_version=None, prompt_position=None, invalid_index_count=None,
        )]
        mock_hybrid.return_value = ([dict(
            candidate, llm_score=80, llm_rank=1, llm_reason="ok",
            prompt_version="rerank_v1", prompt_position=1, invalid_index_count=0,
        )], "llm")
        mock_control.return_value = ([dict(
            candidate, llm_score=70, llm_rank=1, llm_reason="ok",
            prompt_version="rerank_simple_v1", prompt_position=1, invalid_index_count=0,
        )], "llm")

        call_command("run_date_experiment")

        rows = DateSuggestionFeedback.objects.filter(source=DateSuggestionFeedback.SOURCE_EXPERIMENT)
        conversations_count = Conversation.objects.filter(
            user1__email__endswith="@tcc-experiment.bonding.local",
            user2__email__endswith="@tcc-experiment.bonding.local",
        ).count()
        self.assertEqual(rows.count(), conversations_count * 4)

        run_ids = set(rows.values_list("experiment_run_id", flat=True))
        self.assertEqual(len(run_ids), 1)

        variants = set(rows.values_list("variant", flat=True))
        self.assertEqual(variants, {
            DateSuggestionFeedback.VARIANT_AI_PURE,
            DateSuggestionFeedback.VARIANT_DETERMINISTIC_PURE,
            DateSuggestionFeedback.VARIANT_HYBRID_FULL,
            DateSuggestionFeedback.VARIANT_HYBRID_SIMPLE_PROMPT,
        })

    def test_raises_without_gemini_api_key(self):
        from django.core.management.base import CommandError

        with override_settings(GEMINI_API_KEY=""):
            with self.assertRaises(CommandError):
                call_command("run_date_experiment")


class ReportDateExperimentCommandTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="report1@example.com", password="StrongPass123!")
        self.user2 = User.objects.create_user(email="report2@example.com", password="StrongPass123!")
        for index, user in enumerate((self.user1, self.user2), start=1):
            Profile.objects.create(
                user=user, name=f"User {index}", age=20 + index,
                gender=Profile.GENDER_OTHER, sexual_orientation=Profile.ORIENTATION_OTHER,
                course="Computacao",
            )
        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        UserLocationPing.objects.create(user=self.user1, latitude=-2.5300, longitude=-44.3000)

        # Production-like hybrid round: 2 places, deterministic vs LLM order reversed.
        DateSuggestionFeedback.objects.bulk_create([
            DateSuggestionFeedback(
                conversation=self.conversation, place_name="A",
                place_latitude=-2.531, place_longitude=-44.301,
                deterministic_score=0.9, llm_score=60, llm_rank=2, round_id="round-1",
                metadata={"ranking_source": "llm", "invalid_index_count": 1},
            ),
            DateSuggestionFeedback(
                conversation=self.conversation, place_name="B",
                place_latitude=-2.532, place_longitude=-44.302,
                deterministic_score=0.4, llm_score=90, llm_rank=1, round_id="round-1",
                used_at=timezone.now(),
                metadata={"ranking_source": "llm", "invalid_index_count": 1},
            ),
        ])

        self.run_id = "11111111-1111-1111-1111-111111111111"
        DateSuggestionFeedback.objects.create(
            conversation=self.conversation, place_name="Longe",
            place_latitude=-23.55, place_longitude=-46.63,
            source=DateSuggestionFeedback.SOURCE_EXPERIMENT,
            variant=DateSuggestionFeedback.VARIANT_HYBRID_FULL,
            experiment_run_id=self.run_id, round_id="round-exp-1",
            metadata={"ranking_source": "llm", "radius_km": 100},
        )
        DateSuggestionFeedback.objects.create(
            conversation=self.conversation, place_name="Bar Inventado Que Nao Existe",
            place_latitude=None, place_longitude=None,
            source=DateSuggestionFeedback.SOURCE_EXPERIMENT,
            variant=DateSuggestionFeedback.VARIANT_AI_PURE,
            experiment_run_id=self.run_id, round_id="round-exp-2",
            metadata={"known_candidate_names": ["Bar Central", "Restaurante da Praia"]},
        )

    def test_report_computes_expected_metrics(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = tmp.name
        try:
            call_command("report_date_experiment", "--output", output_path, stdout=StringIO())
            with open(output_path) as fh:
                report = json.load(fh)
        finally:
            os.remove(output_path)

        self.assertEqual(report["spearman"]["rounds_included"], 1)
        self.assertEqual(report["usage_rate_by_ranking_source"]["llm"]["used"], 1)
        self.assertEqual(report["invalid_index_discard_rate"]["rounds_with_at_least_one_discard"], 1)
        self.assertEqual(report["experiment_run_id"], self.run_id)

        violation = report["variant_violation_rate"]
        self.assertEqual(violation["hybrid_full"]["violations"], 1)
        self.assertEqual(violation["ai_pure"]["violations"], 1)


class HealthCheckViewTests(TestCase):
    def test_health_check_is_public_and_returns_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ConsentChainTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="consent@example.com", password="StrongPass123!")

    def test_record_consent_builds_a_valid_chain(self):
        first = record_consent(user=self.user, consent_type=ConsentRecord.GENERAL_TERMS)
        second = record_consent(user=self.user, consent_type=ConsentRecord.PRIVACY_POLICY)

        self.assertEqual(second.prev_hash, first.hmac_signature)
        self.assertEqual(verify_chain_integrity(), [])

    def test_verify_chain_integrity_detects_tampering(self):
        # Nao e possivel adulterar uma linha de verdade para testar isso (a
        # trigger WORM bloqueia qualquer UPDATE, inclusive em testes — esse e
        # o comportamento correto). Em vez disso, validamos a deteccao pelo
        # mesmo mecanismo que a protege: recalcular a assinatura com uma
        # chave diferente da usada na criacao do registro deve expor a
        # divergencia entre o hash armazenado e o hash recalculado.
        record = record_consent(user=self.user, consent_type=ConsentRecord.GENERAL_TERMS)
        self.assertEqual(verify_chain_integrity(), [])

        with override_settings(FIELD_ENCRYPTION_KEY="uma-chave-diferente-so-para-este-teste"):
            issues = verify_chain_integrity()

        self.assertTrue(any(issue["id"] == record.id for issue in issues))

    def test_direct_sql_update_is_rejected_by_worm_trigger(self):
        record = record_consent(user=self.user, consent_type=ConsentRecord.GENERAL_TERMS)

        with self.assertRaises(Exception):
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE bonding_consentrecord SET content_hash = %s WHERE id = %s",
                    ["0" * 64, record.id],
                )

    def test_direct_sql_delete_is_rejected_by_worm_trigger(self):
        record = record_consent(user=self.user, consent_type=ConsentRecord.GENERAL_TERMS)

        with self.assertRaises(Exception):
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM bonding_consentrecord WHERE id = %s", [record.id])


class RegisterRequiresConsentTests(TestCase):
    def setUp(self):
        # As versoes vigentes de Termos/Privacidade/TCLE ja existem em
        # qualquer banco (inclusive o de teste) via as migrations de seed
        # 0020_seed_legal_documents e 0024_publish_tcle_and_demo_mode_documents.
        self.client = APIClient()
        self.terms = LegalDocumentVersion.objects.get(
            document_type=LegalDocumentVersion.TERMS_OF_USE, is_current=True
        )
        self.privacy = LegalDocumentVersion.objects.get(
            document_type=LegalDocumentVersion.PRIVACY_POLICY, is_current=True
        )
        self.tcle = LegalDocumentVersion.objects.get(
            document_type=LegalDocumentVersion.RESEARCH_CONSENT, is_current=True
        )

    def _payload(self, **overrides):
        payload = {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "name": "Nova Pessoa",
            "age": 25,
        }
        payload.update(overrides)
        return payload

    def test_registration_without_accepted_documents_is_rejected(self):
        response = self.client.post("/auth/register/", self._payload(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_registration_with_partial_acceptance_is_rejected(self):
        response = self.client.post(
            "/auth/register/",
            self._payload(accepted_document_ids=[self.terms.id]),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_registration_without_tcle_acceptance_is_rejected(self):
        response = self.client.post(
            "/auth/register/",
            self._payload(accepted_document_ids=[self.terms.id, self.privacy.id]),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_registration_with_full_acceptance_creates_chained_consent_records(self):
        response = self.client.post(
            "/auth/register/",
            self._payload(
                accepted_document_ids=[self.terms.id, self.privacy.id, self.tcle.id]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        user = User.objects.get(email="new@example.com")
        records = ConsentRecord.objects.filter(user=user).order_by("id")
        self.assertEqual(
            set(records.values_list("consent_type", flat=True)),
            {
                ConsentRecord.GENERAL_TERMS,
                ConsentRecord.PRIVACY_POLICY,
                ConsentRecord.RESEARCH_CONSENT,
            },
        )
        self.assertEqual(verify_chain_integrity(), [])


class AccountLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="lifecycle@example.com", password="StrongPass123!")
        Profile.objects.create(
            user=self.user,
            name="Pessoa Teste",
            age=25,
            gender=Profile.GENDER_OTHER,
            sexual_orientation=Profile.ORIENTATION_OTHER,
            course="Computacao",
        )
        self.client.force_authenticate(self.user)

    def test_deactivate_requires_correct_password(self):
        response = self.client.post("/account/deactivate/", {"password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_deactivate_with_correct_password_disables_login(self):
        response = self.client.post("/account/deactivate/", {"password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, 204)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=self.user, consent_type=ConsentRecord.ACCOUNT_DEACTIVATION
            ).exists()
        )

    def test_delete_anonymizes_profile_and_disables_login(self):
        original_email = self.user.email

        response = self.client.post("/account/delete/", {"password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, 204)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertNotEqual(self.user.email, original_email)
        self.assertFalse(self.user.has_usable_password())

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.name, "Usuario removido")
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=self.user, consent_type=ConsentRecord.ACCOUNT_DELETION
            ).exists()
        )

    def test_login_reactivates_a_deactivated_account(self):
        deactivate_response = self.client.post(
            "/account/deactivate/", {"password": "StrongPass123!"}, format="json"
        )
        self.assertEqual(deactivate_response.status_code, 204)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

        anonymous_client = APIClient()
        login_response = anonymous_client.post(
            "/api/token/",
            {"email": self.user.email, "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(
            ConsentRecord.objects.filter(
                user=self.user, consent_type=ConsentRecord.ACCOUNT_REACTIVATION
            ).exists()
        )

    def test_login_with_wrong_password_does_not_reactivate_deactivated_account(self):
        self.client.post("/account/deactivate/", {"password": "StrongPass123!"}, format="json")

        anonymous_client = APIClient()
        login_response = anonymous_client.post(
            "/api/token/",
            {"email": self.user.email, "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 401)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_login_does_not_reactivate_a_deleted_account(self):
        self.client.post("/account/delete/", {"password": "StrongPass123!"}, format="json")
        self.user.refresh_from_db()
        deleted_email = self.user.email

        anonymous_client = APIClient()
        login_response = anonymous_client.post(
            "/api/token/",
            {"email": deleted_email, "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 401)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class PaymentDemoModeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="demo@example.com", password="StrongPass123!")
        Profile.objects.create(
            user=self.user,
            name="Pessoa Demo",
            age=25,
            gender=Profile.GENDER_OTHER,
            sexual_orientation=Profile.ORIENTATION_OTHER,
            course="Computacao",
        )
        self.plan = PremiumPlan.objects.create(
            code="gold-demo",
            name="Gold Demo",
            price_monthly="59.90",
        )
        self.client.force_authenticate(self.user)

    @override_settings(PAYMENTS_DEMO_MODE=True)
    def test_demo_mode_activates_plan_without_calling_abacatepay(self):
        with patch("bonding.views.payments.create_abacatepay_pix") as mock_pix, patch(
            "bonding.views.payments.create_abacatepay_billing"
        ) as mock_billing:
            response = self.client.post(
                "/payments/intents/",
                {"plan_id": self.plan.id, "method": "pix", "cpf": ""},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["demo"])
        mock_pix.assert_not_called()
        mock_billing.assert_not_called()

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.premium_tier, "gold-demo")
        self.assertTrue(Subscription.objects.filter(user=self.user, plan=self.plan).exists())

    def test_without_demo_mode_real_abacatepay_flow_is_used(self):
        with patch("bonding.views.payments.create_abacatepay_pix") as mock_pix:
            mock_pix.return_value = {"pix_code": "code123", "qr_code_image": "data:image/png;base64,"}
            response = self.client.post(
                "/payments/intents/",
                {"plan_id": self.plan.id, "method": "pix", "cpf": "12345678901"},
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("demo", response.json())
        mock_pix.assert_called_once()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.premium_tier, "free")

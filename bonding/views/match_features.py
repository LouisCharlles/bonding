from uuid import uuid4

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    Conversation,
    ConversationStageSnapshot,
    DateSuggestionFeedback,
    Match,
    Message,
    Profile,
    UserLocationPing,
)
from ..services.conversation_analysis import INTEREST_MAP, analyze_conversation_interests
from ..services.date_ranking import filter_recently_shown, rerank_suggestions_with_llm
from ..services.external_integrations import IntegrationError, get_overpass_suggestions


class MatchDateSuggestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, match_id):
        match = get_object_or_404(
            Match.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
            id=match_id
        )
        conversation = match.conversation

        ping = UserLocationPing.objects.filter(user=request.user).order_by("-created_at").first()
        if not ping:
            return Response({"detail": "Compartilhe sua localizacao para sugerir um date."}, status=400)

        try:
            radius_km = min(max(int(request.query_params.get("radius", 5)), 1), 100)
        except (ValueError, TypeError):
            radius_km = 5
        radius_meters = radius_km * 1000

        raw_categories = request.query_params.get("categories", "")
        category_ids = [c.strip() for c in raw_categories.split(",") if c.strip()] or None
        search_query = request.query_params.get("query", "").strip() or None

        intent = getattr(getattr(request.user, "profile", None), "relationship_intent", None)

        try:
            candidates = get_overpass_suggestions(
                ping.latitude, ping.longitude, radius_meters,
                intent=intent, category_ids=category_ids, query=search_query,
            )
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        candidates = filter_recently_shown(conversation.id, candidates)

        snapshot = ConversationStageSnapshot.objects.filter(conversation=conversation).first()
        conversation_context = {
            "stage": snapshot.stage if snapshot else None,
            "interests": snapshot.interests if snapshot else [],
            "tipo_role": snapshot.tipo_role if snapshot else None,
        }
        ranked_places, ranking_source = rerank_suggestions_with_llm(candidates, conversation_context, top_n=5)

        if ranked_places:
            round_id = str(uuid4())
            DateSuggestionFeedback.objects.bulk_create([
                DateSuggestionFeedback(
                    conversation=conversation,
                    match=match,
                    place_name=place.get("name") or "",
                    place_latitude=place.get("latitude"),
                    place_longitude=place.get("longitude"),
                    deterministic_score=place.get("deterministic_score"),
                    llm_score=place.get("llm_score"),
                    llm_rank=place.get("llm_rank"),
                    metadata_completeness_score=place.get("metadata_completeness_score"),
                    source=DateSuggestionFeedback.SOURCE_MANUAL,
                    round_id=round_id,
                    metadata={
                        "ranking_source": ranking_source,
                        "llm_reason": place.get("llm_reason"),
                        "prompt_version": place.get("prompt_version"),
                        "prompt_position": place.get("prompt_position"),
                        "invalid_index_count": place.get("invalid_index_count"),
                    },
                )
                for place in ranked_places
            ])

        return Response(ranked_places, status=200)


class ConversationDateReadinessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
            id=conversation_id
        )

        snapshot = ConversationStageSnapshot.objects.filter(conversation_id=conversation_id).first()
        if snapshot and settings.GEMINI_API_KEY:
            interests = snapshot.interests or []
            message_count = Message.objects.filter(
                conversation_id=conversation_id,
                message_type=Message.TYPE_TEXT,
                is_system=False,
            ).count()
            return Response({
                "ready": snapshot.stage in ConversationStageSnapshot.READY_STAGES,
                "message_count": message_count,
                "detected_interests": interests,
                "suggested_categories": [
                    cid for interest in interests for cid in INTEREST_MAP[interest]["category_ids"]
                ],
                "category_labels": [INTEREST_MAP[i]["label"] for i in interests],
                "stage": snapshot.stage,
                "stage_confidence": snapshot.stage_confidence,
                "source": "gemini",
            }, status=200)

        result = analyze_conversation_interests(conversation_id)

        return Response({
            "ready": result["ready"],
            "message_count": result["message_count"],
            "detected_interests": result["detected_interests"],
            "suggested_categories": result["foursquare_categories"],
            "category_labels": result["category_labels"],
            "source": "heuristic",
        }, status=200)


class CupidoRecommendationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        if profile.premium_tier != Profile.PREMIUM_PLATINUM:
            return Response({"detail": "CUpido disponivel apenas no plano mais alto."}, status=403)

        candidates = Profile.objects.exclude(user=request.user).prefetch_related("interests")[:10]
        recommendations = []
        user_interests = {interest.id for interest in profile.interests.all()}
        for candidate in candidates:
            overlap = len(user_interests.intersection({interest.id for interest in candidate.interests.all()}))
            score = min(99, 50 + overlap * 10)
            recommendations.append({
                "profile_uuid": str(candidate.uuid),
                "name": candidate.name,
                "score": score,
                "reasons": [
                    f"{overlap} interesses em comum" if overlap else "Potencial complementaridade",
                    f"Intencao alinhada: {candidate.relationship_intent}",
                ],
                "opening_suggestion": f"Comece falando sobre {candidate.course or 'a rotina no campus'} para criar conexao.",
            })
        recommendations.sort(key=lambda item: item["score"], reverse=True)
        return Response(recommendations[:5], status=200)
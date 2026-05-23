from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Conversation, Match, Profile, UserLocationPing
from ..services.conversation_analysis import analyze_conversation_interests
from ..services.external_integrations import IntegrationError, get_foursquare_suggestions


class MatchDateSuggestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, match_id):
        match = get_object_or_404(
            Match.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
            id=match_id
        )

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
            places = get_foursquare_suggestions(
                ping.latitude, ping.longitude, radius_meters,
                intent=intent, category_ids=category_ids, query=search_query,
            )
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        return Response(places, status=200)


class ConversationDateReadinessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.filter(Q(user1=request.user) | Q(user2=request.user)),
            id=conversation_id
        )

        result = analyze_conversation_interests(conversation_id)
        
        return Response({
            "ready": result["ready"],
            "message_count": result["message_count"],
            "detected_interests": result["detected_interests"],
            "suggested_categories": result["foursquare_categories"],
            "category_labels": result["category_labels"],
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
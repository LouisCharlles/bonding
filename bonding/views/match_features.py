from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Match, Profile, UserLocationPing
from ..services.external_integrations import IntegrationError, estimate_distance_km, get_google_midpoint_suggestions


class MatchDateSuggestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, match_id):
        match = Match.objects.filter(id=match_id).first()
        if not match or request.user.id not in [match.user1_id, match.user2_id]:
            return Response({"detail": "Match nao encontrado."}, status=404)

        other_user = match.user2 if match.user1_id == request.user.id else match.user1
        if not request.user.profile.allow_date_suggestions or not other_user.profile.allow_date_suggestions:
            return Response({"detail": "Sugestoes nao habilitadas por ambos os usuarios."}, status=400)

        origin = UserLocationPing.objects.filter(user=request.user).first()
        destination = UserLocationPing.objects.filter(user=other_user).first()
        if not origin or not destination:
            return Response({"detail": "Localizacao recente indisponivel para um dos usuarios."}, status=400)

        try:
            places = get_google_midpoint_suggestions(
                (origin.latitude, origin.longitude),
                (destination.latitude, destination.longitude),
            )
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)

        response = []
        for place in places:
            location = place.get("geometry", {}).get("location", {})
            distance = estimate_distance_km(
                (origin.latitude, origin.longitude),
                (location.get("lat", origin.latitude), location.get("lng", origin.longitude)),
            )
            response.append({
                "name": place.get("name"),
                "rating": place.get("rating"),
                "vicinity": place.get("vicinity"),
                "distance_km": distance,
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={location.get('lat')},{location.get('lng')}",
            })
        return Response(response, status=200)


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

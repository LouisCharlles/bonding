from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.external_integrations import IntegrationError, search_spotify_tracks


class SpotifyTrackSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = str(request.query_params.get("q", "")).strip()
        if not query:
            return Response([], status=200)
        try:
            results = search_spotify_tracks(query)
        except IntegrationError as error:
            return Response({"detail": str(error)}, status=400)
        return Response(results, status=200)

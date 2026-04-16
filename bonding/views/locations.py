from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Location, UserLocationPing
from ..serializers import LocationSerializer


class LocationCreateOrRetrieveView(generics.GenericAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        city = request.data.get("city")
        state = request.data.get("state")
        country = request.data.get("country")
        neighborhood = request.data.get("neighborhood")

        if not any([latitude, longitude, city, state, country]):
            return Response(
                {"error": "Informe coordenadas ou pelo menos cidade/estado/pais."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        location, _ = Location.objects.get_or_create(
            city=city,
            state=state,
            country=country,
            defaults={
                "latitude": latitude,
                "longitude": longitude,
                "neighborhood": neighborhood,
            },
        )

        changed = False
        for field, value in {
            "latitude": latitude,
            "longitude": longitude,
            "neighborhood": neighborhood,
        }.items():
            if value not in [None, ""] and getattr(location, field) != value:
                setattr(location, field, value)
                changed = True
        if changed:
            location.save()

        serializer = self.get_serializer(location)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserLocationPingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        if latitude in [None, ""] or longitude in [None, ""]:
            return Response({"detail": "latitude e longitude sao obrigatorios."}, status=400)

        ping = UserLocationPing.objects.create(
            user=request.user,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=request.data.get("accuracy_meters"),
        )
        return Response({
            "id": ping.id,
            "latitude": ping.latitude,
            "longitude": ping.longitude,
            "accuracy_meters": ping.accuracy_meters,
            "created_at": ping.created_at,
        }, status=201)

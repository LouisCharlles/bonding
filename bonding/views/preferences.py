from rest_framework import viewsets, permissions
from ..models import Preference
from ..serializers import PreferenceSerializer


class PreferenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

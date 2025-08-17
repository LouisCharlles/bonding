from rest_framework import viewsets, permissions
from ..models import Preference
from ..serial import PreferenceSerializer

class PreferenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar todas as preferências disponíveis.
    Usuários podem apenas ler a lista de preferências.
    """
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

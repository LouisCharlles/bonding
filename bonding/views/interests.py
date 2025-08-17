from rest_framework import viewsets, permissions
from ..models import Interest
from ..serial import InterestSerializer
class InterestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar todos os interesses disponíveis.
    Usuários podem apenas ler a lista de interesses.
    """
    queryset = Interest.objects.all()
    serializer_class = InterestSerializer
    permission_classes = [permissions.IsAuthenticated]
from rest_framework import viewsets, permissions
from ..models import Interest
from ..serializers import InterestSerializer


class InterestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Interest.objects.all()
    serializer_class = InterestSerializer
    permission_classes = [permissions.IsAuthenticated]

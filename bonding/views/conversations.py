# bonding/views.py

from rest_framework import viewsets, permissions
from ..models import Conversation
from ..serial import ConversationSerializer

class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Garante que um usuário só pode ver as suas próprias conversas.
        """
        user = self.request.user
        return Conversation.objects.filter(user1=user) | Conversation.objects.filter(user2=user)
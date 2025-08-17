# bonding/views.py

from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from ..models import Message, Conversation
from ..serial import MessageSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtra as mensagens para apenas as que pertencem a uma conversa do usuário logado.
        """
        user = self.request.user
        return Message.objects.filter(conversation__user1=user) | Message.objects.filter(conversation__user2=user)

    def perform_create(self, serializer):
        """
        Associa a mensagem ao usuário logado e garante que ele faz parte da conversa.
        """
        conversation = serializer.validated_data.get('conversation')
        if self.request.user not in [conversation.user1, conversation.user2]:
            raise PermissionDenied("Você não pode enviar mensagens nesta conversa.")
            
        serializer.save(sender=self.request.user)
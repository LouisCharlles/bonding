from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from ..models import Connection, Conversation
from ..serial import ConnectionSerializer

class ConnectionViewSet(viewsets.ModelViewSet):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = ['post']

    def perform_create(self, serializer):
        from_user = self.request.user
        to_user = serializer.validated_data.get('to_user')

        if from_user == to_user:
            raise PermissionError("Você não pode dar like em si mesmo.")
        instance = serializer.save(from_user=from_user)

        reciprocal_connection = Connection.objects.filter(
            from_user=to_user,
            to_user=from_user,
            status='like'
        ).exists()

        if instance.status == 'like' and reciprocal_connection:
            Conversation.objects.create(user1=from_user,user2=to_user)
            return Response({'match':True},status=status.HTTP_201_CREATED)
        return Response({'match':False},status=status.HTTP_201_CREATED)
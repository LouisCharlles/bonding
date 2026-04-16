import uuid

from django.db.models import Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from ..models import Conversation, VideoCallSession
from ..serializers import VideoCallSessionSerializer


class VideoCallSessionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = VideoCallSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoCallSession.objects.filter(
            Q(conversation__user1=self.request.user) | Q(conversation__user2=self.request.user)
        )

    def perform_create(self, serializer):
        conversation = serializer.validated_data["conversation"]
        if self.request.user not in [conversation.user1, conversation.user2]:
            raise PermissionDenied("Voce nao participa desta conversa.")
        serializer.save(
            initiated_by=self.request.user,
            room_name=f"bonding-{conversation.id}-{uuid.uuid4().hex[:12]}",
        )

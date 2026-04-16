from django.db.models import Q
from rest_framework import permissions, viewsets

from ..models import Conversation
from ..serializers import ConversationSerializer
from ..services.blocks import get_blocked_user_ids


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Conversation.objects.select_related(
            "user1",
            "user2",
            "user1__profile__location",
            "user2__profile__location",
        ).prefetch_related(
            "messages__sender",
            "user1__profile__photos",
            "user1__profile__interests",
            "user1__profile__preferences",
            "user2__profile__photos",
            "user2__profile__interests",
            "user2__profile__preferences",
        ).filter(Q(user1=self.request.user) | Q(user2=self.request.user))
        blocked_ids = get_blocked_user_ids(self.request.user)
        if blocked_ids:
            queryset = queryset.exclude(Q(user1_id__in=blocked_ids) | Q(user2_id__in=blocked_ids))
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include_messages"] = self.action == "retrieve"
        return context

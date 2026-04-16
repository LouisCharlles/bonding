from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Match, Story, StoryReaction, StoryView
from ..serializers import StoryReactionSerializer, StorySerializer
from ..services.blocks import get_blocked_user_ids


class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_matched_user_ids(self, user):
        matched_user_ids = []
        matches = Match.objects.filter(Q(user1=user) | Q(user2=user), is_active=True)
        for match in matches:
            matched_user_ids.append(match.user2_id if match.user1_id == user.id else match.user1_id)
        return matched_user_ids

    def get_queryset(self):
        user = self.request.user
        blocked_ids = get_blocked_user_ids(user)
        matched_user_ids = self.get_matched_user_ids(user)

        queryset = Story.objects.select_related("author").prefetch_related("views__viewer", "reactions__user").filter(
            is_active=True,
            expires_at__gt=timezone.now(),
        )

        if self.action == "feed":
            queryset = queryset.filter(
                author_id__in=matched_user_ids,
            ).filter(
                Q(visibility=Story.VISIBILITY_MATCHES) | Q(visibility=Story.VISIBILITY_ALL)
            )
        elif self.action in {"register_view", "react", "retrieve"}:
            queryset = queryset.filter(
                Q(author=user)
                | (
                    Q(author_id__in=matched_user_ids)
                    & (Q(visibility=Story.VISIBILITY_MATCHES) | Q(visibility=Story.VISIBILITY_ALL))
                )
            )
        else:
            queryset = queryset.filter(author=user)

        if blocked_ids:
            queryset = queryset.exclude(author_id__in=blocked_ids)
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        story = self.get_object()
        if story.author != self.request.user:
            raise PermissionDenied("Voce nao pode editar este story.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Voce nao pode remover este story.")
        instance.delete()

    @action(detail=False, methods=["get"], url_path="feed")
    def feed(self, request):
        serializer = self.get_serializer(self.get_queryset()[:30], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="views")
    def register_view(self, request, pk=None):
        story = self.get_object()
        view, created = StoryView.objects.get_or_create(story=story, viewer=request.user)
        return Response({"id": view.id, "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reactions")
    def react(self, request, pk=None):
        story = self.get_object()
        emoji = request.data.get("emoji", "").strip()
        if not emoji:
            raise ValidationError({"emoji": "Emoji e obrigatorio."})
        reaction, created = StoryReaction.objects.get_or_create(
            story=story,
            user=request.user,
            emoji=emoji,
        )
        serializer = StoryReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

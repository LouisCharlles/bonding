from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Match, Story, StoryReaction, StoryView
from ..serializers import StoryReactionSerializer, StorySerializer
from ..services.blocks import get_blocked_user_ids
from ..services.realtime import publish_to_users


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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        client_request_id = str(request.data.get("client_request_id", "")).strip() or None
        if client_request_id:
            existing_story = Story.objects.filter(
                author=request.user,
                client_request_id=client_request_id,
                is_active=True,
            ).first()
            if existing_story:
                serializer = self.get_serializer(existing_story)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            if not client_request_id:
                raise
            existing_story = Story.objects.filter(
                author=request.user,
                client_request_id=client_request_id,
                is_active=True,
            ).first()
            if not existing_story:
                raise
            serializer = self.get_serializer(existing_story)
            return Response(serializer.data, status=status.HTTP_200_OK)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        story = serializer.save(author=self.request.user)
        self._publish_story_event(story, "story.created")

    def perform_update(self, serializer):
        story = self.get_object()
        if story.author != self.request.user:
            raise PermissionDenied("Voce nao pode editar este story.")
        story = serializer.save()
        self._publish_story_event(story, "story.updated")

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Voce nao pode remover este story.")
        story_id = instance.id
        recipients = [self.request.user.id, *self.get_matched_user_ids(self.request.user)]
        instance.delete()
        publish_to_users(
            "stories",
            recipients,
            {
                "type": "story.deleted",
                "entity": "story",
                "data": {"id": story_id},
                "timestamp": timezone.now().isoformat(),
            },
        )

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
        self._publish_story_event(story, "story.updated")
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    def _publish_story_event(self, story, event_type):
        recipients = [story.author_id, *self.get_matched_user_ids(story.author)]
        publish_to_users(
            "stories",
            recipients,
            {
                "type": event_type,
                "entity": "story",
                "data": StorySerializer(story, context={"request": self.request}).data,
                "timestamp": timezone.now().isoformat(),
            },
        )

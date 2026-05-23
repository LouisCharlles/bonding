from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Match, Message, Story, StoryReaction, StoryView
from ..serializers import MessageSerializer, StoryReactionSerializer, StorySerializer
from ..services.blocks import get_blocked_user_ids, is_blocked_pair
from ..services.realtime import publish_group_event, publish_to_users


class StoryViewSet(viewsets.ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_matched_user_ids(self, user, include_inactive=False):
        qs = Match.objects.filter(Q(user1=user) | Q(user2=user))
        if not include_inactive:
            qs = qs.filter(is_active=True)
        pairs = qs.values_list("user1_id", "user2_id")
        return [u2 if u1 == user.id else u1 for u1, u2 in pairs]

    def _base_queryset(self):
        user = self.request.user
        blocked_ids = get_blocked_user_ids(user)
        queryset = Story.objects.select_related(
            "author",
            "author__profile",
        ).prefetch_related(
            "views__viewer",
            "reactions__user",
        ).filter(
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        if blocked_ids:
            queryset = queryset.exclude(author_id__in=blocked_ids)
        return queryset

    def _get_active_match_queryset(self, user):
        return Match.objects.select_related("conversation", "user1", "user2").filter(
            Q(user1=user) | Q(user2=user),
            is_active=True,
        )

    def _get_visible_stories_queryset(self):
        user = self.request.user
        matches_data = self._get_active_match_queryset(user).values_list("user1_id", "user2_id")
        match_ids = {u2 if u1 == user.id else u1 for u1, u2 in matches_data}
        return self._base_queryset().filter(
            Q(author=user)
            | (
                Q(author_id__in=match_ids)
                & (Q(visibility=Story.VISIBILITY_MATCHES) | Q(visibility=Story.VISIBILITY_ALL))
            )
        )

    def _get_feed_queryset(self):
        return self._get_visible_stories_queryset().exclude(author=self.request.user)

    def _get_match_for_story(self, story):
        user = self.request.user
        if story.author_id == user.id:
            raise PermissionDenied("Nao e possivel responder ao proprio story.")

        match = self._get_active_match_queryset(user).filter(
            Q(user1=story.author) | Q(user2=story.author),
        ).first()
        if not match or not match.conversation_id:
            raise PermissionDenied("Voce nao pode interagir com este story sem match ativo.")
        if is_blocked_pair(user, story.author):
            raise PermissionDenied("Voce nao pode interagir com stories deste usuario.")
        return match

    def _publish_message_created(self, message):
        publish_group_event(
            f"conversation_{message.conversation_id}",
            {
                "type": "message.created",
                "entity": "message",
                "conversation_id": message.conversation_id,
                "data": MessageSerializer(message, context={"request": self.request}).data,
                "timestamp": message.created_at.isoformat(),
            },
        )

    def _create_story_reply_message(self, story, content):
        normalized_content = str(content or "").strip()
        if not normalized_content:
            raise ValidationError({"content": "Conteudo e obrigatorio."})

        match = self._get_match_for_story(story)
        conversation = match.conversation
        message = Message.objects.create(
            conversation=conversation,
            sender=self.request.user,
            content=normalized_content,
            message_type=Message.TYPE_STORY_REPLY,
            story=story,
        )
        conversation.last_message = "Respondeu ao story"
        conversation.save(update_fields=["last_message", "updated_at"])
        self._publish_message_created(message)
        return message

    def get_queryset(self):
        if self.action == "list":
            return self._base_queryset().filter(author=self.request.user)
        if self.action == "feed":
            return self._get_feed_queryset()
        return self._get_visible_stories_queryset()

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
        story = serializer.save(author=self.request.user, is_active=True)
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
        if created and story.author_id != request.user.id:
            self._create_story_reply_message(story, emoji)
        serializer = StoryReactionSerializer(reaction)
        self._publish_story_event(story, "story.updated")
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reply")
    def reply(self, request, pk=None):
        story = self.get_object()
        content = request.data.get("content", "")
        message = self._create_story_reply_message(story, content)
        self._publish_story_event(story, "story.updated")
        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

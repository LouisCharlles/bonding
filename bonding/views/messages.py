from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Conversation, Message, MessageReaction
from ..serializers import MessageReactionSerializer, MessageSerializer
from ..services.blocks import get_blocked_user_ids, is_blocked_pair
from ..services.realtime import publish_group_event


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        queryset = Message.objects.select_related(
            "sender",
            "conversation",
            "story",
            "story__author",
        ).prefetch_related(
            "reactions__user",
        ).filter(
            Q(conversation__user1=self.request.user) | Q(conversation__user2=self.request.user)
        )
        blocked_ids = get_blocked_user_ids(self.request.user)
        if blocked_ids:
            queryset = queryset.exclude(
                Q(conversation__user1_id__in=blocked_ids) | Q(conversation__user2_id__in=blocked_ids)
            )
        conversation_id = self.request.query_params.get("conversation")
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        return queryset

    def _publish_message_created(self, message):
        payload = MessageSerializer(message, context={"request": self.request}).data
        publish_group_event(
            f"conversation_{message.conversation_id}",
            {
                "type": "message.created",
                "entity": "message",
                "conversation_id": message.conversation_id,
                "data": payload,
                "timestamp": message.created_at.isoformat(),
            },
        )

    def _get_message_preview(self, message):
        return message.content or (
            "Respondeu ao story"
            if message.message_type == Message.TYPE_STORY_REPLY
            else message.message_type
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        client_request_id = str(request.data.get("client_request_id", "")).strip() or None
        if client_request_id:
            existing_message = Message.objects.filter(
                sender=request.user,
                client_request_id=client_request_id,
            ).select_related("sender", "conversation").first()
            if existing_message:
                serializer = self.get_serializer(existing_message)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            if not client_request_id:
                raise
            existing_message = Message.objects.filter(
                sender=request.user,
                client_request_id=client_request_id,
            ).select_related("sender", "conversation").first()
            if not existing_message:
                raise
            serializer = self.get_serializer(existing_message)
            return Response(serializer.data, status=status.HTTP_200_OK)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        conversation = serializer.validated_data["conversation"]
        if self.request.user not in [conversation.user1, conversation.user2]:
            raise PermissionDenied("Voce nao pode enviar mensagens nesta conversa.")
        other_user = conversation.user2 if conversation.user1_id == self.request.user.id else conversation.user1
        if is_blocked_pair(self.request.user, other_user):
            raise PermissionDenied("Voce nao pode enviar mensagens para este usuario.")

        message = serializer.save(sender=self.request.user)
        conversation.last_message = self._get_message_preview(message)
        conversation.save(update_fields=["last_message", "updated_at"])
        cache.delete_many([f"inbox:{conversation.user1_id}", f"inbox:{conversation.user2_id}"])
        self._publish_message_created(message)
        self._maybe_trigger_intent_analysis(message)

    def _maybe_trigger_intent_analysis(self, message):
        if message.message_type != Message.TYPE_TEXT:
            return
        count = Message.objects.filter(
            conversation_id=message.conversation_id,
            message_type=Message.TYPE_TEXT,
            is_system=False,
        ).count()
        if count >= 10 and count % 10 == 0:
            from ..tasks import check_date_intent_task
            check_date_intent_task.delay(message.conversation_id)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        conversation_id = request.data.get("conversation_id")
        if not conversation_id:
            return Response({"detail": "conversation_id e obrigatorio."}, status=400)

        conversation = Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user),
            id=conversation_id,
        ).first()
        if not conversation:
            raise PermissionDenied("Conversa nao encontrada.")

        updated = conversation.messages.filter(read=False).exclude(sender=request.user).update(read=True)
        if updated:
            publish_group_event(
                f"conversation_{conversation.id}",
                {
                    "type": "message.read",
                    "entity": "message",
                    "conversation_id": conversation.id,
                    "data": {
                        "reader_id": request.user.id,
                        "updated": updated,
                    },
                    "timestamp": timezone.now().isoformat(),
                },
            )
        return Response({"updated": updated})

    @action(detail=True, methods=["post"], url_path="reactions")
    def reactions(self, request, pk=None):
        message = self.get_object()
        emoji = request.data.get("emoji", "").strip()
        if not emoji:
            raise ValidationError({"emoji": "Emoji e obrigatorio."})
        reaction = MessageReaction.objects.filter(message=message, user=request.user).first()
        created = reaction is None
        if reaction is None:
            reaction = MessageReaction.objects.create(
                message=message,
                user=request.user,
                emoji=emoji,
            )
        elif reaction.emoji != emoji:
            reaction.emoji = emoji
            reaction.save(update_fields=["emoji"])
        serializer = MessageReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="consume-view-once")
    def consume_view_once(self, request, pk=None):
        message = self.get_object()
        if not message.is_view_once:
            raise ValidationError({"detail": "Esta mensagem nao e de visualizacao unica."})
        if message.sender_id == request.user.id:
            raise PermissionDenied("Apenas o destinatario pode consumir a midia.")
        if message.consumed_at:
            return Response({"detail": "Midia ja consumida.", "consumed_at": message.consumed_at}, status=200)
        message.consumed_at = timezone.now()
        message.save(update_fields=["consumed_at"])
        publish_group_event(
            f"conversation_{message.conversation_id}",
            {
                "type": "message.updated",
                "entity": "message",
                "conversation_id": message.conversation_id,
                "data": MessageSerializer(message).data,
                "timestamp": message.consumed_at.isoformat(),
            },
        )
        return Response({"detail": "Midia consumida.", "consumed_at": message.consumed_at}, status=200)

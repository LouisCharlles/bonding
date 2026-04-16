from django.db import transaction
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from ..models import Connection, Conversation, Match, Profile
from ..serializers import ConnectionSerializer, MatchSerializer, DiscoverProfileSerializer
from ..services.blocks import get_blocked_user_ids, is_blocked_pair
from ..services.wallet import award_daily_like_ribbon, can_unlock_likes_session, unlock_likes_session


class ConnectionViewSet(viewsets.ModelViewSet):
    queryset = Connection.objects.select_related("from_user", "to_user")
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        blocked_ids = get_blocked_user_ids(self.request.user)
        queryset = self.queryset.filter(from_user=self.request.user)
        if blocked_ids:
            queryset = queryset.exclude(to_user_id__in=blocked_ids)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from_user = request.user
        to_user = serializer.validated_data["to_user"]
        status_value = serializer.validated_data["status"]

        if from_user == to_user:
            raise ValidationError({"to_user": "Voce nao pode interagir consigo mesmo."})
        if is_blocked_pair(from_user, to_user):
            raise ValidationError({"to_user": "Interacao indisponivel para este usuario."})

        connection, _ = Connection.objects.update_or_create(
            from_user=from_user,
            to_user=to_user,
            defaults={"status": status_value},
        )

        reciprocal = Connection.objects.filter(
            from_user=to_user,
            to_user=from_user,
            status__in=[Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE],
        ).first()

        is_match = status_value in [
            Connection.STATUS_LIKE,
            Connection.STATUS_SUPERLIKE,
        ] and reciprocal is not None

        payload = self.get_serializer(connection).data
        payload["match"] = None

        if is_match:
            connection.is_mutual = True
            reciprocal.is_mutual = True
            connection.save(update_fields=["is_mutual", "updated_at"])
            reciprocal.save(update_fields=["is_mutual", "updated_at"])

            ordered_users = sorted([from_user, to_user], key=lambda user: user.id)
            conversation, _ = Conversation.objects.get_or_create(
                user1=ordered_users[0],
                user2=ordered_users[1],
            )
            match, _ = Match.objects.get_or_create(
                user1=ordered_users[0],
                user2=ordered_users[1],
                defaults={"conversation": conversation},
            )
            if match.conversation_id != conversation.id:
                match.conversation = conversation
                match.save(update_fields=["conversation"])
            payload["match"] = MatchSerializer(match, context={"request": request}).data

        if status_value in [Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE]:
            award_daily_like_ribbon(from_user)

        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="matches")
    def matches(self, request):
        matches = Match.objects.select_related(
            "conversation",
            "user1__profile__location",
            "user2__profile__location",
        ).prefetch_related(
            "user1__profile__photos",
            "user1__profile__interests",
            "user1__profile__preferences",
            "user2__profile__photos",
            "user2__profile__interests",
            "user2__profile__preferences",
        ).filter(Q(user1=request.user) | Q(user2=request.user))
        serializer = MatchSerializer(matches, many=True, context={"request": request})
        return Response(serializer.data)

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="undo")
    def undo(self, request):
        latest_connection = self.get_queryset().order_by("-updated_at", "-created_at").first()
        if not latest_connection:
            return Response(
                {"detail": "Nenhuma interacao encontrada para desfazer."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reciprocal = Connection.objects.filter(
            from_user=latest_connection.to_user,
            to_user=latest_connection.from_user,
        ).first()

        affected_match = Match.objects.filter(
            Q(user1=latest_connection.from_user, user2=latest_connection.to_user)
            | Q(user1=latest_connection.to_user, user2=latest_connection.from_user)
        ).first()

        payload = {
            "undone_connection_id": latest_connection.id,
            "affected_match_id": affected_match.id if affected_match else None,
        }

        latest_connection.delete()

        if reciprocal and reciprocal.is_mutual:
            reciprocal.is_mutual = False
            reciprocal.save(update_fields=["is_mutual", "updated_at"])

        if affected_match:
            pair_connections = Connection.objects.filter(
                Q(from_user=affected_match.user1, to_user=affected_match.user2)
                | Q(from_user=affected_match.user2, to_user=affected_match.user1),
                status__in=[Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE],
                is_mutual=True,
            )

            if pair_connections.count() < 2:
                pair_connections.update(is_mutual=False)
                conversation = affected_match.conversation
                affected_match.delete()
                if conversation and not Match.objects.filter(conversation=conversation).exists():
                    conversation.delete()

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="likes-received")
    def likes_received(self, request):
        profile = getattr(request.user, "profile", None)
        blocked_ids = get_blocked_user_ids(request.user)
        connections = Connection.objects.select_related("from_user__profile__location").prefetch_related(
            "from_user__profile__photos",
            "from_user__profile__interests",
            "from_user__profile__preferences",
        ).filter(
            to_user=request.user,
            status__in=[Connection.STATUS_LIKE, Connection.STATUS_SUPERLIKE],
        )
        if blocked_ids:
            connections = connections.exclude(from_user_id__in=blocked_ids)

        visible = bool(profile and profile.premium_tier != Profile.PREMIUM_FREE) or can_unlock_likes_session(request.user)
        items = []
        for connection in connections:
            serialized = DiscoverProfileSerializer(connection.from_user.profile, context={"request": request}).data
            items.append({
                "connection_id": connection.id,
                "status": connection.status,
                "visible": visible,
                "profile": serialized if visible else None,
            })
        return Response({"visible": visible, "results": items}, status=200)

    @action(detail=False, methods=["post"], url_path="likes-received/unlock")
    def unlock_likes(self, request):
        profile = getattr(request.user, "profile", None)
        if profile and profile.premium_tier != Profile.PREMIUM_FREE:
            return Response({"detail": "Premium ja possui acesso completo."}, status=200)
        unlock = unlock_likes_session(request.user)
        return Response({"detail": "Curtidas desbloqueadas.", "unlocked_until": unlock.unlocked_until}, status=201)

    def perform_update(self, serializer):
        connection = self.get_object()
        if connection.from_user != self.request.user:
            raise PermissionDenied("Voce nao pode atualizar esta interacao.")
        serializer.save()

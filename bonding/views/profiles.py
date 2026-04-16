from django.db.models import Q
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.exceptions import PermissionDenied

from ..models import Connection, Match, Profile
from ..serializers import DiscoverProfileSerializer, ProfileSerializer
from ..services.blocks import get_blocked_user_ids


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        base_queryset = Profile.objects.select_related("user", "location").prefetch_related(
            "interests",
            "preferences",
            "photos",
        )

        if self.action == "discover":
            swiped_user_ids = list(
                Connection.objects.filter(from_user=user).values_list("to_user_id", flat=True)
            )
            blocked_user_ids = get_blocked_user_ids(user)
            matched_users = Match.objects.filter(Q(user1=user) | Q(user2=user))
            matched_user_ids = []
            for match in matched_users:
                matched_user_ids.append(match.user2_id if match.user1_id == user.id else match.user1_id)

            queryset = base_queryset.exclude(user=user).filter(is_invisible_mode=False)
            if swiped_user_ids:
                queryset = queryset.exclude(user_id__in=swiped_user_ids)
            if matched_user_ids:
                queryset = queryset.exclude(user_id__in=matched_user_ids)
            if blocked_user_ids:
                queryset = queryset.exclude(user_id__in=blocked_user_ids)
            profile = getattr(user, "profile", None)
            if profile:
                queryset = queryset.filter(
                    age__gte=profile.min_preferred_age,
                    age__lte=profile.max_preferred_age,
                )
            return queryset

        if self.action == "list":
            return base_queryset.filter(user=user)

        return base_queryset.filter(user=user)

    @decorators.action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return response.Response(
                {"detail": "Perfil ainda nao foi criado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(profile)
        return response.Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], url_path="discover")
    def discover(self, request):
        serializer = DiscoverProfileSerializer(
            self.get_queryset()[:20],
            many=True,
            context={"request": request},
        )
        return response.Response(serializer.data)

    def perform_create(self, serializer):
        if hasattr(self.request.user, "profile"):
            raise PermissionDenied("Usuario ja possui um perfil.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        profile = self.get_object()
        if profile.user != self.request.user:
            raise PermissionDenied("Voce nao tem permissao para editar este perfil.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("Voce nao tem permissao para deletar este perfil.")
        instance.delete()

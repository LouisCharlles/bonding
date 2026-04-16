from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from ..models import Photo
from ..serializers import PhotoSerializer


class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Photo.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "profile", None)
        if not profile:
            raise PermissionDenied("Crie um perfil antes de adicionar fotos.")
        serializer.save(profile=profile)

    def perform_update(self, serializer):
        if serializer.instance.profile.user != self.request.user:
            raise PermissionDenied("Voce nao tem permissao para editar esta foto.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.profile.user != self.request.user:
            raise PermissionDenied("Voce nao tem permissao para deletar esta foto.")
        instance.delete()

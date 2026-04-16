from django.db import IntegrityError, transaction
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from ..models import Photo
from ..serializers import PhotoSerializer


class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile:
            raise PermissionDenied("Crie um perfil antes de adicionar fotos.")

        client_request_id = str(request.data.get("client_request_id", "")).strip() or None
        if client_request_id:
            existing_photo = Photo.objects.filter(
                profile=profile,
                client_request_id=client_request_id,
            ).first()
            if existing_photo:
                serializer = self.get_serializer(existing_photo)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            if not client_request_id:
                raise
            existing_photo = Photo.objects.filter(
                profile=profile,
                client_request_id=client_request_id,
            ).first()
            if not existing_photo:
                raise
            serializer = self.get_serializer(existing_photo)
            return Response(serializer.data, status=status.HTTP_200_OK)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from ..models import Photo
from ..serial import PhotoSerializer

class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Photo.objects.filter(perfil__user=self.request.user)
    
    def perform_create(self, serializer):
        profile = self.request.user.profile
        if not profile:
            raise PermissionDenied("Crie um perfil antes de adicionar fotos.")
        serializer.save(perfil=profile)
    def perform_destroy(self, instance):
        """
        Permite que apenas o dono da foto a delete.
        """
        if instance.perfil.user != self.request.user:
            raise PermissionDenied("Você não tem permissão para deletar esta foto.")
        instance.delete()
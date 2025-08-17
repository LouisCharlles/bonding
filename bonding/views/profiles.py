from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from ..models import Profile
from ..serial import ProfileSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user

        if self.action in ['retrieve','update','destroy']:
            return Profile.objects.filter(user=user)
        
        return Profile.objects.exclude(user=user)
    
    def perform_create(self, serializer):
        if hasattr(self.request.user,'profile'):
            raise PermissionDenied("Usuário já possui um perfil.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        profile = self.get_object()
        if profile.user != self.request.user:
            raise PermissionDenied("Você não tem permissão para editar este perfil.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied("Você não tem permissão para deletar este perfil.")
        instance.delete()
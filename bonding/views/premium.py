from rest_framework import mixins, permissions, viewsets

from ..models import PremiumPlan, Subscription
from ..serializers import PremiumPlanSerializer, SubscriptionSerializer


class PremiumPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PremiumPlan.objects.filter(is_active=True)
    serializer_class = PremiumPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubscriptionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.select_related("plan").filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=Subscription.STATUS_ACTIVE)

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import UnlockSession, Wallet
from ..serializers import RewardEventSerializer, UnlockSessionSerializer, WalletLedgerSerializer, WalletSerializer
from ..services.wallet import award_video_ribbons, get_or_create_wallet


class WalletViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        wallet = get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet).data)

    @action(detail=False, methods=["get"], url_path="ledger")
    def ledger(self, request):
        wallet = get_or_create_wallet(request.user)
        return Response(WalletLedgerSerializer(wallet.entries.all()[:100], many=True).data)

    @action(detail=False, methods=["get"], url_path="unlocks")
    def unlocks(self, request):
        unlocks = UnlockSession.objects.filter(user=request.user)
        return Response(UnlockSessionSerializer(unlocks, many=True).data)

    @action(detail=False, methods=["post"], url_path="reward-video")
    def reward_video(self, request):
        success, message = award_video_ribbons(request.user)
        return Response({"success": success, "detail": message}, status=200 if success else 400)

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.account import deactivate_account, delete_account


class AccountDeactivateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        if not password or not request.user.check_password(password):
            return Response({"detail": "Senha incorreta."}, status=status.HTTP_400_BAD_REQUEST)

        deactivate_account(request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        if not password or not request.user.check_password(password):
            return Response({"detail": "Senha incorreta."}, status=status.HTTP_400_BAD_REQUEST)

        delete_account(request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

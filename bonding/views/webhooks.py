import logging
import urllib.parse

from django.conf import settings
from django.http import HttpResponse
from django.views import View

from ..models import User
from ..services.google_ssv import verify_ssv_signature
from ..services.wallet import award_video_ribbons
from ..services.realtime import publish_group_event

logger = logging.getLogger(__name__)


class GoogleRewardWebhookView(View):
    """
    Server-Side Verification (SSV) callback called by Google's servers after
    the user completes watching a rewarded ad. The request is signed with
    ECDSA-SHA256 using Google's public keys.

    Google requires HTTP 200 on success. On failure (bad signature etc.),
    we return 400 so Google retries. We return 200 for unknown users to
    prevent flood from retries on stale custom_data values.
    """

    def get(self, request):
        if not settings.GOOGLE_SSV_ENABLED:
            return HttpResponse(status=200)

        params = request.GET
        key_id = params.get("key_id", "")
        signature = params.get("signature", "")
        user_id = params.get("custom_data", "")

        if not key_id or not signature or not user_id:
            logger.warning("Google SSV: missing required params key_id=%s user_id=%s", key_id, user_id)
            return HttpResponse(status=400)

        # The signed content is the full query string with 'signature' removed,
        # preserving the original param order as sent by Google.
        raw_query = request.META.get("QUERY_STRING", "")
        signed_query = "&".join(
            part for part in raw_query.split("&")
            if not part.startswith("signature=")
        )

        if not verify_ssv_signature(signed_query, key_id, signature):
            logger.warning("Google SSV: invalid signature for user_id=%s key_id=%s", user_id, key_id)
            return HttpResponse(status=400)

        try:
            user = User.objects.get(pk=int(user_id))
        except (User.DoesNotExist, ValueError):
            logger.warning("Google SSV: user not found user_id=%s", user_id)
            return HttpResponse(status=200)

        success, detail = award_video_ribbons(user)
        logger.info("Google SSV: award_video_ribbons user_id=%s success=%s detail=%s", user_id, success, detail)

        if success:
            publish_group_event(
                f"stories_{user.id}",
                {"type": "wallet.updated", "entity": "wallet"},
            )

        return HttpResponse(status=200)

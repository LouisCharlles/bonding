import logging
from datetime import timezone as dt_timezone

from django.utils import timezone

from setup.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=2, default_retry_delay=10)
def check_date_intent_task(self, conversation_id: int):
    """
    Triggered every 10th text message in a conversation.
    Sends last 10 messages to Gemini for intent classification.
    If SUGGEST_DATE with confidence > 80, fetches OSM places and
    pushes a 'date.intent.detected' WebSocket event to the conversation group.
    """
    from .models import Conversation, Message, UserLocationPing
    from .services.gemini import analyze_chat_intent
    from .services.external_integrations import get_foursquare_suggestions, IntegrationError
    from .services.realtime import publish_group_event

    try:
        conversation = Conversation.objects.select_related("user1", "user2").get(pk=conversation_id)
    except Conversation.DoesNotExist:
        logger.warning("check_date_intent_task: conversation %s not found", conversation_id)
        return

    raw_messages = (
        Message.objects.filter(
            conversation_id=conversation_id,
            message_type=Message.TYPE_TEXT,
            is_system=False,
        )
        .order_by("-created_at")
        .select_related("sender")[:10]
    )

    if not raw_messages:
        return

    user1_id = conversation.user1_id
    # Build anonymous labels ("User A" / "User B") to avoid leaking user IDs to Gemini
    messages = [
        {
            "label": "User A" if m.sender_id == user1_id else "User B",
            "content": m.content,
        }
        for m in reversed(raw_messages)
    ]

    result = analyze_chat_intent(messages)

    if result.get("intent") != "SUGGEST_DATE" or result.get("confidence", 0) <= 80:
        return

    entities = result.get("entities") or {}
    query = entities.get("cuisine_or_amenity") or "restaurante"

    # Use the most recent location ping of either conversation participant
    ping = (
        UserLocationPing.objects.filter(user_id__in=[conversation.user1_id, conversation.user2_id])
        .order_by("-created_at")
        .first()
    )
    if not ping:
        logger.info(
            "check_date_intent_task: no location ping for conversation %s — skipping OSM search",
            conversation_id,
        )
        suggestions = []
    else:
        try:
            suggestions = get_foursquare_suggestions(
                ping.latitude,
                ping.longitude,
                radius_meters=5000,
                query=query,
            )[:5]
        except IntegrationError:
            logger.exception("check_date_intent_task: OSM search failed for conversation %s", conversation_id)
            suggestions = []

    publish_group_event(
        f"conversation_{conversation_id}",
        {
            "type": "date.intent.detected",
            "entity": "date_suggestion",
            "conversation_id": conversation_id,
            "data": {
                "intent": result["intent"],
                "confidence": result["confidence"],
                "entities": entities,
                "suggestions": suggestions,
            },
            "timestamp": timezone.now().isoformat(),
        },
    )
    logger.info(
        "check_date_intent_task: published date.intent.detected for conversation %s (confidence=%s)",
        conversation_id,
        result["confidence"],
    )

import logging
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from setup.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=2, default_retry_delay=10)
def check_date_intent_task(self, conversation_id: int):
    """
    Triggered every 10th text message in a conversation.
    Sends last 10 messages to Gemini for intent classification.
    If SUGGEST_DATE with confidence above settings.DATE_SUGGESTION_CONFIDENCE_THRESHOLD,
    and the cooldown window has elapsed, runs the deterministic-filter + LLM
    semantic-rerank pipeline for nearby places and pushes a
    'date.intent.detected' WebSocket event to the conversation group. When the
    cooldown is still active, republishes the cached suggestion set instead of
    recomputing.
    """
    from .models import Conversation, ConversationStageSnapshot, DateSuggestionFeedback, Match, Message, UserLocationPing
    from .services.gemini import analyze_chat_intent, analyze_conversation_stage
    from .services.external_integrations import get_overpass_suggestions, IntegrationError
    from .services.date_ranking import filter_recently_shown, rerank_suggestions_with_llm
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

    current_text_count = Message.objects.filter(
        conversation_id=conversation_id,
        message_type=Message.TYPE_TEXT,
        is_system=False,
    ).count()

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
    stage_result = analyze_conversation_stage(messages)

    snapshot, _created = ConversationStageSnapshot.objects.update_or_create(
        conversation_id=conversation_id,
        defaults={
            "stage": stage_result.get("stage", ConversationStageSnapshot.STAGE_QUEBRA_GELO),
            "stage_confidence": stage_result.get("stage_confidence", 0),
            "interests": stage_result.get("interests", []),
            "tipo_role": stage_result.get("tipo_role"),
        },
    )

    if result.get("intent") != "SUGGEST_DATE" or result.get("confidence", 0) <= settings.DATE_SUGGESTION_CONFIDENCE_THRESHOLD:
        return

    entities = result.get("entities") or {}

    messages_since_last = current_text_count - snapshot.last_suggested_message_count
    time_since_last = timezone.now() - snapshot.last_suggested_at if snapshot.last_suggested_at else None
    cooldown_active = (
        snapshot.last_suggested_at is not None
        and messages_since_last <= settings.DATE_SUGGESTION_COOLDOWN_MESSAGES
        and time_since_last is not None
        and time_since_last <= timedelta(hours=settings.DATE_SUGGESTION_COOLDOWN_HOURS)
    )

    if cooldown_active:
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
                    "suggestions": snapshot.cached_suggestions,
                    "stage": stage_result.get("stage"),
                    "stage_confidence": stage_result.get("stage_confidence"),
                    "interests": stage_result.get("interests", []),
                    "tipo_role": stage_result.get("tipo_role"),
                    "cache_hit": True,
                },
                "timestamp": timezone.now().isoformat(),
            },
        )
        logger.info(
            "check_date_intent_task: cooldown active for conversation %s — reused cached suggestions",
            conversation_id,
        )
        return

    query = entities.get("cuisine_or_amenity") or _query_from_interests(stage_result) or "restaurante"

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
        ranked_places, ranking_source = [], "deterministic_fallback"
    else:
        try:
            candidates = get_overpass_suggestions(
                ping.latitude,
                ping.longitude,
                radius_meters=5000,
                query=query,
            )
            candidates = filter_recently_shown(conversation_id, candidates)
            conversation_context = {
                "stage": stage_result.get("stage"),
                "interests": stage_result.get("interests", []),
                "tipo_role": stage_result.get("tipo_role"),
                "recent_messages": messages,
            }
            ranked_places, ranking_source = rerank_suggestions_with_llm(candidates, conversation_context, top_n=5)
        except IntegrationError:
            logger.exception("check_date_intent_task: OSM search failed for conversation %s", conversation_id)
            ranked_places, ranking_source = [], "deterministic_fallback"

    round_id = str(uuid4())
    if ranked_places:
        match = Match.objects.filter(conversation_id=conversation_id).first()
        DateSuggestionFeedback.objects.bulk_create([
            DateSuggestionFeedback(
                conversation=conversation,
                match=match,
                place_name=place.get("name") or "",
                place_latitude=place.get("latitude"),
                place_longitude=place.get("longitude"),
                deterministic_score=place.get("deterministic_score"),
                llm_score=place.get("llm_score"),
                llm_rank=place.get("llm_rank"),
                metadata_completeness_score=place.get("metadata_completeness_score"),
                source=DateSuggestionFeedback.SOURCE_AUTOMATIC,
                round_id=round_id,
                metadata={
                    "ranking_source": ranking_source,
                    "llm_reason": place.get("llm_reason"),
                    "prompt_version": place.get("prompt_version"),
                    "prompt_position": place.get("prompt_position"),
                    "invalid_index_count": place.get("invalid_index_count"),
                },
            )
            for place in ranked_places
        ])

    snapshot.last_suggested_at = timezone.now()
    snapshot.last_suggested_message_count = current_text_count
    snapshot.cached_suggestions = ranked_places
    snapshot.save(update_fields=["last_suggested_at", "last_suggested_message_count", "cached_suggestions"])

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
                "suggestions": ranked_places,
                "stage": stage_result.get("stage"),
                "stage_confidence": stage_result.get("stage_confidence"),
                "interests": stage_result.get("interests", []),
                "tipo_role": stage_result.get("tipo_role"),
                "ranking_source": ranking_source,
                "round_id": round_id,
                "cache_hit": False,
            },
            "timestamp": timezone.now().isoformat(),
        },
    )
    logger.info(
        "check_date_intent_task: published date.intent.detected for conversation %s (confidence=%s, ranking_source=%s)",
        conversation_id,
        result["confidence"],
        ranking_source,
    )


def _query_from_interests(stage_result: dict) -> str | None:
    """Falls back to the label of the first detected interest when Gemini's
    intent classifier didn't extract a specific cuisine/amenity entity."""
    from .services.conversation_analysis import INTEREST_MAP

    interests = stage_result.get("interests") or []
    if not interests:
        return None
    return INTEREST_MAP.get(interests[0], {}).get("label")

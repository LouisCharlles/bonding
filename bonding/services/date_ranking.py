import json
import logging
import random
from datetime import timedelta

import google.generativeai as genai
from django.conf import settings
from django.utils import timezone

from ..models import DateSuggestionFeedback

logger = logging.getLogger(__name__)

# Exported so prepare_training_data-style tooling can reuse the exact prompt,
# matching the convention in bonding/services/gemini.py.
_RERANK_PROMPT = RERANK_PROMPT_TEMPLATE = """\
Você é um sistema de recomendação semântica de locais para encontros (dates) entre casais de um app de namoro.
Você recebe uma lista de locais candidatos, já filtrados deterministicamente por categoria e distância, e o
contexto da conversa do casal. Sua tarefa é REORDENAR os candidatos pela relevância semântica para ESSE casal
específico, considerando o estágio do relacionamento, os interesses demonstrados e o tom da conversa.

Contexto da conversa:
- Estágio: {stage}
- Interesses detectados: {interests}
- Tipo de rolê sugerido: {tipo_role}
- Últimas mensagens:
{chat_history}

Candidatos (índice: nome | distância | endereço | completude de dados 0-1):
{candidates_block}

Retorne EXATAMENTE este formato JSON, com no máximo {top_n} itens, ordenados do mais para o menos relevante:
{{
  "ranking": [
    {{"index": inteiro (índice do candidato acima), "score": inteiro 0 a 100, "reason": "motivo curto em português"}}
  ]
}}
"""

# Bump this whenever _RERANK_PROMPT's text changes, so each persisted
# suggestion can be traced back to the exact prompt that produced it.
RERANK_PROMPT_VERSION = "rerank_v1"


def _deterministic_fallback(ordered_candidates, top_n, invalid_index_count=None):
    fallback_places = []
    for rank, place in enumerate(ordered_candidates[:top_n], start=1):
        fallback_place = dict(place)
        fallback_place["llm_score"] = None
        fallback_place["llm_rank"] = rank
        fallback_place["llm_reason"] = None
        fallback_place["prompt_version"] = None
        fallback_place["prompt_position"] = None
        fallback_place["invalid_index_count"] = invalid_index_count
        fallback_places.append(fallback_place)
    return fallback_places, "deterministic_fallback"


def rank_deterministic_only(candidates: list[dict], top_n: int = 5):
    """Ranking without the semantic rerank stage — used by the 'Variante
    Determinística Pura' experiment. Reuses the same ordering/tagging logic
    as the production fallback."""
    ordered = sorted(candidates, key=lambda c: c.get("deterministic_score") or 0, reverse=True)
    places, _source = _deterministic_fallback(ordered, top_n)
    return places


def rerank_suggestions_with_llm(
    candidates: list[dict],
    conversation_context: dict | None = None,
    top_n: int = 5,
    prompt_template: str | None = None,
    prompt_version: str | None = None,
):
    """
    Reorders a deterministically-filtered shortlist of places by semantic fit
    to the couple's conversation, using Gemini. Returns (ranked_places, ranking_source)
    where ranking_source is "llm" or "deterministic_fallback".

    Falls back to the deterministic order (by `deterministic_score`) on any
    missing API key, request failure, or malformed response — mirrors the
    fallback convention in bonding/services/gemini.py.

    `prompt_template`/`prompt_version` let experiment variants (see
    bonding/services/date_experiment_variants.py) reuse this same validated
    pipeline with an alternate prompt while keeping the index-validation and
    fallback guarantees intact.
    """
    conversation_context = conversation_context or {}
    if not candidates:
        return [], "deterministic_fallback"

    prompt_template = prompt_template or _RERANK_PROMPT
    prompt_version = prompt_version or RERANK_PROMPT_VERSION

    ordered = sorted(candidates, key=lambda c: c.get("deterministic_score") or 0, reverse=True)

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping semantic rerank")
        return _deterministic_fallback(ordered, top_n)

    # Presentation order is shuffled independently of the deterministic rank
    # order so that a candidate's position in the prompt is decoupled from
    # its deterministic score — without this, "position in the prompt" and
    # "deterministic rank" are perfectly confounded and position bias can't
    # be measured separately from score bias.
    presentation_order = list(range(len(ordered)))
    random.shuffle(presentation_order)

    candidates_block = "\n".join(
        f"{prompt_index}: {ordered[original_index].get('name')} | {ordered[original_index].get('distance_km')}km | "
        f"{ordered[original_index].get('vicinity') or 'sem endereço'} | "
        f"completude={ordered[original_index].get('metadata_completeness_score')}"
        for prompt_index, original_index in enumerate(presentation_order)
    )
    recent_messages = conversation_context.get("recent_messages") or []
    prompt = prompt_template.format(
        stage=conversation_context.get("stage") or "desconhecido",
        interests=", ".join(conversation_context.get("interests") or []) or "nenhum detectado",
        tipo_role=conversation_context.get("tipo_role") or "não especificado",
        chat_history="\n".join(f"{m['label']}: {m['content']}" for m in recent_messages) or "(sem mensagens recentes)",
        candidates_block=candidates_block,
        top_n=top_n,
    )

    invalid_index_count = None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        ranking = data.get("ranking") or []

        invalid_index_count = 0
        ranked_places = []
        used_prompt_indices = set()
        for item in ranking:
            prompt_index = item.get("index")
            if (
                not isinstance(prompt_index, int)
                or prompt_index < 0
                or prompt_index >= len(presentation_order)
                or prompt_index in used_prompt_indices
            ):
                invalid_index_count += 1
                continue
            used_prompt_indices.add(prompt_index)
            original_index = presentation_order[prompt_index]
            place = dict(ordered[original_index])
            place["llm_score"] = item.get("score")
            place["llm_rank"] = len(ranked_places) + 1
            place["llm_reason"] = item.get("reason")
            place["prompt_version"] = prompt_version
            place["prompt_position"] = prompt_index + 1
            ranked_places.append(place)
            if len(ranked_places) >= top_n:
                break

        if not ranked_places:
            raise ValueError("Gemini returned no valid ranking indices")

        for place in ranked_places:
            place["invalid_index_count"] = invalid_index_count

        return ranked_places, "llm"
    except Exception:
        logger.exception("Gemini semantic rerank failed — falling back to deterministic ranking")
        return _deterministic_fallback(ordered, top_n, invalid_index_count=invalid_index_count)


def filter_recently_shown(conversation_id, candidates: list[dict], dedup_days: int | None = None) -> list[dict]:
    """Excludes candidates already shown (and not used) for this conversation
    within the last `dedup_days` (default settings.DATE_SUGGESTION_DEDUP_DAYS)."""
    if not candidates or not conversation_id:
        return candidates

    dedup_days = dedup_days if dedup_days is not None else settings.DATE_SUGGESTION_DEDUP_DAYS
    cutoff = timezone.now() - timedelta(days=dedup_days)
    recently_shown = DateSuggestionFeedback.objects.filter(
        conversation_id=conversation_id,
        created_at__gte=cutoff,
        used_at__isnull=True,
    ).values_list("place_name", "place_latitude", "place_longitude")
    excluded = {(name, round(lat, 4), round(lon, 4)) for name, lat, lon in recently_shown}
    if not excluded:
        return candidates

    return [
        c for c in candidates
        if (c.get("name"), round(c.get("latitude", 0), 4), round(c.get("longitude", 0), 4)) not in excluded
    ]


def mark_suggestion_used(conversation_id, place_name, latitude, longitude) -> bool:
    """Marks the most recent unused shown-suggestion feedback row matching
    this place (by name + coordinates) as used. Returns True if a row was
    updated. Called when a date_suggestion message referencing this place is
    sent in the chat — see bonding/views/messages.py."""
    if not conversation_id or not place_name or latitude is None or longitude is None:
        return False

    try:
        lat_r, lon_r = round(float(latitude), 4), round(float(longitude), 4)
    except (TypeError, ValueError):
        return False

    candidates = DateSuggestionFeedback.objects.filter(
        conversation_id=conversation_id,
        place_name=place_name,
        used_at__isnull=True,
    ).order_by("-created_at")

    for feedback in candidates:
        if round(feedback.place_latitude, 4) == lat_r and round(feedback.place_longitude, 4) == lon_r:
            feedback.used_at = timezone.now()
            feedback.save(update_fields=["used_at"])
            return True
    return False

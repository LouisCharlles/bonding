"""Four controlled pipeline variants used to isolate which component of the
hybrid architecture (deterministic geospatial filter vs. semantic LLM rerank)
is responsible for the observed recommendation quality — the experimental
design described in the TCC's "Hipótese" defense answer:

- IA Pura: the LLM freely suggests places with no deterministic grounding at
  all (baseline expected to hallucinate geographically).
- Determinística Pura: the deterministic filter/score only, no semantic
  rerank.
- Híbrida Completa: the production pipeline as implemented.
- Híbrida de Controle (Prompt Simplificado): same rerank stage, but with the
  explicit scoring rubric stripped from the prompt, to attribute any quality
  gain to the rubric itself rather than to "having an LLM look at the list".

Only used by bonding/management/commands/run_date_experiment.py and its
tests — not part of the production request path.
"""
import json
import logging

import google.generativeai as genai
from django.conf import settings

from .date_ranking import rank_deterministic_only, rerank_suggestions_with_llm

logger = logging.getLogger(__name__)

VARIANT_AI_PURE = "ai_pure"
VARIANT_DETERMINISTIC_PURE = "deterministic_pure"
VARIANT_HYBRID_FULL = "hybrid_full"
VARIANT_HYBRID_SIMPLE_PROMPT = "hybrid_control_simple_prompt"
ALL_VARIANTS = [
    VARIANT_AI_PURE,
    VARIANT_DETERMINISTIC_PURE,
    VARIANT_HYBRID_FULL,
    VARIANT_HYBRID_SIMPLE_PROMPT,
]

AI_PURE_PROMPT_VERSION = "ai_pure_v1"
_AI_PURE_PROMPT = AI_PURE_PROMPT_TEMPLATE = """\
Você é um assistente de recomendação de locais para encontros (dates) de um app de namoro.
Um casal está conversando e você deve sugerir lugares reais para eles saírem, usando livremente
seu conhecimento geral — você NÃO recebeu nenhuma lista de candidatos e não tem acesso a busca
em mapas ou geolocalização.

Cidade onde o casal mora: {user_city}

Contexto da conversa:
- Estágio: {stage}
- Interesses detectados: {interests}
- Tipo de rolê sugerido: {tipo_role}
- Últimas mensagens:
{chat_history}

Sugira até {top_n} lugares específicos (nomes reais de estabelecimentos, não categorias
genéricas) que combinem com o clima da conversa acima.

Retorne EXATAMENTE este formato JSON:
{{
  "suggestions": [
    {{"name": "nome do estabelecimento", "city": "cidade onde esse lugar fica",
      "estimated_address": "endereço aproximado, se souber, ou nulo",
      "reason": "motivo curto em português"}}
  ]
}}
"""

RERANK_SIMPLE_PROMPT_VERSION = "rerank_simple_v1"
_RERANK_SIMPLE_PROMPT = RERANK_SIMPLE_PROMPT_TEMPLATE = """\
Você é um sistema de recomendação de locais para um casal que está namorando pelo app.

Conversa do casal:
{chat_history}

Aqui está uma lista de lugares candidatos:
{candidates_block}

Escolha até {top_n} lugares dessa lista e ordene do que você acha melhor para o pior.

Retorne EXATAMENTE este formato JSON:
{{
  "ranking": [
    {{"index": inteiro (índice do candidato acima), "score": inteiro 0 a 100, "reason": "motivo curto"}}
  ]
}}
"""


def run_ai_pure(conversation_context: dict | None, user_city: str, top_n: int = 5) -> list[dict]:
    """Baseline de controle: o modelo tenta recomendar locais sem nenhum
    filtro espacial determinístico. Sem fallback determinístico — a ausência
    de rede de segurança geográfica é o próprio ponto do teste."""
    conversation_context = conversation_context or {}

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping ai_pure variant")
        return []

    recent_messages = conversation_context.get("recent_messages") or []
    prompt = _AI_PURE_PROMPT.format(
        user_city=user_city,
        stage=conversation_context.get("stage") or "desconhecido",
        interests=", ".join(conversation_context.get("interests") or []) or "nenhum detectado",
        tipo_role=conversation_context.get("tipo_role") or "não especificado",
        chat_history="\n".join(f"{m['label']}: {m['content']}" for m in recent_messages) or "(sem mensagens recentes)",
        top_n=top_n,
    )

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
        suggestions = data.get("suggestions") or []
    except Exception:
        logger.exception("ai_pure variant failed")
        return []

    places = []
    for rank, item in enumerate(suggestions[:top_n], start=1):
        places.append({
            "name": item.get("name") or "",
            "declared_city": item.get("city"),
            "estimated_address": item.get("estimated_address"),
            "llm_score": None,
            "llm_rank": rank,
            "llm_reason": item.get("reason"),
            "prompt_version": AI_PURE_PROMPT_VERSION,
            "prompt_position": None,
            "invalid_index_count": None,
        })
    return places


def run_deterministic_pure(candidates: list[dict], top_n: int = 5) -> list[dict]:
    """Sistema operando sem a etapa de reordenação semântica final."""
    return rank_deterministic_only(candidates, top_n=top_n)


def run_hybrid_full(candidates: list[dict], conversation_context: dict | None, top_n: int = 5):
    """O pipeline final, tal como implementado em produção."""
    return rerank_suggestions_with_llm(candidates, conversation_context, top_n=top_n)


def run_hybrid_control_simple_prompt(candidates: list[dict], conversation_context: dict | None, top_n: int = 5):
    """Execução do reordenamento final sem a estrutura de pontuação e
    critérios explícitos do prompt de produção."""
    return rerank_suggestions_with_llm(
        candidates,
        conversation_context,
        top_n=top_n,
        prompt_template=_RERANK_SIMPLE_PROMPT,
        prompt_version=RERANK_SIMPLE_PROMPT_VERSION,
    )

import json
import logging

import google.generativeai as genai
from django.conf import settings

from .conversation_analysis import INTEREST_MAP

logger = logging.getLogger(__name__)

# Exported so prepare_training_data can reuse the exact same prompt template
_INTENT_PROMPT = INTENT_PROMPT_TEMPLATE = """\
Você é um analisador de intenções de encontros.
Analise as mensagens abaixo e extraia a intenção, o nível de confiança (0 a 100), o tipo de local/comida e o momento sugerido.

Retorne EXATAMENTE este formato JSON:
{{
  "intent": "SUGGEST_DATE" ou "NONE",
  "confidence": inteiro,
  "entities": {{
    "cuisine_or_amenity": "ex: sushi, cafe, bar, pizza" ou nulo,
    "time": "ex: amanhã, sexta à noite" ou nulo
  }}
}}

Mensagens:
{chat_history}
"""

INTENT_PROMPT_VERSION = "intent_v1"


def analyze_chat_intent(messages: list[dict]) -> dict:
    """
    Receives a list of dicts with keys 'label' and 'content'.
    Returns Gemini's intent classification as a dict.
    Falls back to {"intent": "NONE", "confidence": 0} on any error.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping intent analysis")
        return {"intent": "NONE", "confidence": 0, "entities": {}}

    chat_history = "\n".join(f"{m['label']}: {m['content']}" for m in messages)
    prompt = _INTENT_PROMPT.format(chat_history=chat_history)

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception:
        logger.exception("Gemini intent analysis failed for conversation")
        return {"intent": "NONE", "confidence": 0, "entities": {}}


# Exported so prepare_training_data can reuse the exact same prompt template
_STAGE_PROMPT = STAGE_PROMPT_TEMPLATE = """\
Você é um analisador de estágio de relacionamento e interesses em conversas de um app de namoro.
Classifique o ESTÁGIO da conversa e os INTERESSES/TÓPICOS discutidos.

Estágios possíveis (escolha exatamente um):
- "quebra_gelo": cumprimentos, perguntas superficiais, ainda não há rapport.
- "rapport": trocam informações pessoais, piadas, começam a se conhecer.
- "interesse_mutuo": demonstram afinidade clara, flertam, fazem planos hipotéticos.
- "pronto_para_role": há sinais explícitos ou fortes de querer se encontrar pessoalmente.

Interesses possíveis (liste todos os aplicáveis, pode ser vazio):
food, coffee, bars, outdoors, arts, movies, nightlife, sports, shopping

Retorne EXATAMENTE este formato JSON:
{{
  "stage": "quebra_gelo" ou "rapport" ou "interesse_mutuo" ou "pronto_para_role",
  "stage_confidence": inteiro de 0 a 100,
  "interests": ["food", "bars"],
  "tipo_role": "romantico" ou "casual" ou "praia" ou "bar" ou "gastronomico" ou "cinema" ou "cultural" ou "shopping" ou "role_noturno" ou nulo
}}

Mensagens:
{chat_history}
"""

STAGE_PROMPT_VERSION = "stage_v1"


def analyze_conversation_stage(messages: list[dict]) -> dict:
    """
    Receives a list of dicts with keys 'label' and 'content'.
    Classifies the conversation's stage/intimacy level and detected interests.
    Falls back to a neutral result on any error or missing API key.
    """
    fallback = {
        "stage": "quebra_gelo",
        "stage_confidence": 0,
        "interests": [],
        "tipo_role": None,
    }

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping stage analysis")
        return fallback

    chat_history = "\n".join(f"{m['label']}: {m['content']}" for m in messages)
    prompt = _STAGE_PROMPT.format(chat_history=chat_history)

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        # Defensive normalization: keep only known interests, so the foursquare
        # category mapping downstream never breaks on an unexpected label.
        data["interests"] = [i for i in data.get("interests", []) if i in INTEREST_MAP]
        return data
    except Exception:
        logger.exception("Gemini stage analysis failed for conversation")
        return fallback

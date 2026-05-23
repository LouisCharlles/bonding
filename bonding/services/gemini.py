import json
import logging

import google.generativeai as genai
from django.conf import settings

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
            model_name="gemini-1.5-flash",
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

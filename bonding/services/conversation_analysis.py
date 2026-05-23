from ..models import Message

READINESS_THRESHOLD = 15

INTEREST_MAP = {
    "food": {
        "keywords": ["comer", "restaurante", "jantar", "almoço", "sushi", "pizza", "comida", "gastronomia", "hamburguer", "culinária", "lanche", "refeição"],
        "category_ids": ["13065", "13376"],
        "label": "Restaurantes",
    },
    "coffee": {
        "keywords": ["café", "cafezinho", "cappuccino", "coffee", "barista", "xícara"],
        "category_ids": ["13035"],
        "label": "Café",
    },
    "bars": {
        "keywords": ["bar", "cerveja", "drink", "chopp", "happy hour", "coquetél", "beber", "boteco"],
        "category_ids": ["13003", "13046"],
        "label": "Bares",
    },
    "outdoors": {
        "keywords": ["parque", "praia", "trilha", "natureza", "piquenique", "jardim", "ao ar livre", "caminhada"],
        "category_ids": ["16032", "16034", "10056"],
        "label": "Ao ar livre",
    },
    "arts": {
        "keywords": ["museu", "arte", "galeria", "teatro", "exposição", "cultura", "pintura", "escultura"],
        "category_ids": ["10019", "10013", "10000"],
        "label": "Arte e Cultura",
    },
    "movies": {
        "keywords": ["cinema", "filme", "sessão", "pipoca", "estreia", "série", "animação"],
        "category_ids": ["10025"],
        "label": "Cinema",
    },
    "nightlife": {
        "keywords": ["balada", "festa", "show", "boate", "noite", "clube", "dançar", "rave"],
        "category_ids": ["10046", "10032"],
        "label": "Vida noturna",
    },
    "sports": {
        "keywords": ["esporte", "academia", "futebol", "corrida", "bike", "yoga", "natação", "crossfit", "tênis", "vôlei"],
        "category_ids": ["18000", "18008"],
        "label": "Esportes",
    },
    "shopping": {
        "keywords": ["shopping", "loja", "comprar", "moda", "roupa", "outlet"],
        "category_ids": ["17069", "17000"],
        "label": "Shopping",
    },
}

CATEGORY_LABELS = {
    interest: data["label"]
    for interest, data in INTEREST_MAP.items()
}


def analyze_conversation_interests(conversation_id):
    messages = Message.objects.filter(
        conversation_id=conversation_id,
        message_type=Message.TYPE_TEXT,
        is_system=False,
    ).values_list("content", flat=True)

    message_count = len(messages)
    full_text = " ".join(messages).lower()

    detected_interests = []
    foursquare_categories = []

    for interest, data in INTEREST_MAP.items():
        if any(keyword in full_text for keyword in data["keywords"]):
            detected_interests.append(interest)
            foursquare_categories.extend(data["category_ids"])

    foursquare_categories = list(dict.fromkeys(foursquare_categories))

    return {
        "ready": message_count >= READINESS_THRESHOLD,
        "message_count": message_count,
        "detected_interests": detected_interests,
        "foursquare_categories": foursquare_categories,
        "category_labels": [INTEREST_MAP[i]["label"] for i in detected_interests],
    }

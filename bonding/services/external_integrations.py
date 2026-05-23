import json
import base64
import random
from math import radians, sin, cos, sqrt, atan2
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class IntegrationError(RuntimeError):
    pass


def _http_json(method, url, headers=None, data=None):
    req_headers = headers or {}
    
    # Adicionando um User-Agent para evitar que o Cloudflare/WAF bloqueie a chamada
    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "BondingApp/1.0 (Development)"

    request = Request(
        url,
        method=method,
        headers=req_headers,
        data=data,
    )
    try:
        with urlopen(request) as response:
            payload = response.read().decode("utf-8")
            if not payload.strip():
                return {}
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                print(f"\n❌ [DEBUG API] Resposta não-JSON (Firewall/Redirecionamento):\n{payload}\n")
                raise IntegrationError("A API retornou um formato HTML inesperado.")
                
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        print(f"\n❌ [DEBUG API] Erro HTTP {error.code}:\n{body}\n")
        raise IntegrationError(f"{method} {url} falhou: {error.code} {body}") from error
_ABACATEPAY_BASE = "https://api.abacatepay.com/v1"


def _abacatepay_headers():
    api_key = getattr(settings, "ABACATEPAY_API_KEY", "")
    if not api_key:
        raise IntegrationError("ABACATEPAY_API_KEY nao configurada.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_abacatepay_billing(amount_brl_cents, user, plan, cpf=""):
    """Cria billing AbacatePay para pagamento com cartão. Retorna {'billing_id', 'checkout_url'}."""
    frontend_url = getattr(settings, "FRONTEND_URL", "")
    payload = json.dumps({
        "frequency": "ONE_TIME",
        "methods": ["PIX", "CARD"],
        "products": [{
            "externalId": f"plan_{plan.id}",
            "name": f"Bonding {plan.name}",
            "description": plan.description,
            "quantity": 1,
            "price": amount_brl_cents,
        }],
        "returnUrl": f"{frontend_url}/app/premium",
        "completionUrl": f"{frontend_url}/app/premium",
        "customer": {
            "name": user.get_full_name() or user.email,
            "email": user.email,
            "cellphone": "",
            "taxId": cpf,
        },
        "metadata": {"user_id": str(user.id), "plan_id": str(plan.id)},
    }).encode("utf-8")
    data = _http_json(
        "POST",
        f"{_ABACATEPAY_BASE}/billing/create",
        headers=_abacatepay_headers(),
        data=payload,
    )
    billing = data.get("data", {})
    return {"billing_id": billing["id"], "checkout_url": billing["url"]}


def create_abacatepay_pix(amount_brl_cents, user, plan, cpf):
    """Cria QR Code PIX via AbacatePay. Retorna {'pix_id', 'pix_code', 'qr_code_image'}."""
    payload = json.dumps({
        "amount": amount_brl_cents,
        "description": f"Bonding {plan.name}",
        "expiresIn": 3600,
        "customer": {
            "name": user.get_full_name() or user.email,
            "email": user.email,
            "taxId": cpf,
            "cellphone": "",
        },
        "metadata": {"user_id": str(user.id), "plan_id": str(plan.id)},
    }).encode("utf-8")
    data = _http_json(
        "POST",
        f"{_ABACATEPAY_BASE}/pixQrCode/create",
        headers=_abacatepay_headers(),
        data=payload,
    )
    d = data.get("data", {})
    # 1. Adicione este print para visualizarmos a resposta real no terminal!
    print(f"\n💰 [DEBUG ABACATEPAY PIX]: {d}\n")
    
    # 2. Use o .get() para evitar o KeyError se a imagem não vier
    return {
        "pix_id": d.get("id"), 
        "pix_code": d.get("brCode"), # O "Copia e Cola"
        "qr_code_image": d.get("brCodeImage", "") # Se não existir, retorna string vazia
    }
  
def verify_abacatepay_webhook(request_token):
    """Verifica token de webhook AbacatePay enviado como query param ?token=."""
    expected = getattr(settings, "ABACATEPAY_WEBHOOK_TOKEN", "")
    if not expected:
        raise IntegrationError("ABACATEPAY_WEBHOOK_TOKEN nao configurado.")
    if request_token != expected:
        raise IntegrationError("Token do webhook AbacatePay invalido.")


def get_google_midpoint_suggestions(origin, destination, radius_meters=2500):
    if not getattr(settings, "GOOGLE_MAPS_API_KEY", ""):
        raise IntegrationError("GOOGLE_MAPS_API_KEY nao configurada.")

    midpoint = ((origin[0] + destination[0]) / 2, (origin[1] + destination[1]) / 2)
    query = urlencode({
        "location": f"{midpoint[0]},{midpoint[1]}",
        "radius": radius_meters,
        "keyword": "cafeteria coffee date",
        "key": settings.GOOGLE_MAPS_API_KEY,
    })
    response = _http_json(
        "GET",
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{query}",
    )
    return response.get("results", [])[:5]


# OpenStreetMap intent → OSM tags
_OSM_INTENT_TAGS = {
    "friendship": ["amenity=cafe", "leisure=park", "tourism=museum", "amenity=restaurant"],
    "casual":     ["amenity=restaurant", "amenity=bar", "amenity=cafe", "amenity=fast_food", "amenity=cinema"],
    "serious":    ["amenity=restaurant", "tourism=museum", "amenity=cinema", "amenity=theatre", "leisure=park"],
    "exploring":  ["amenity=bar", "amenity=cafe", "amenity=restaurant", "amenity=cinema", "tourism=attraction"],
}
_OSM_DEFAULT_TAGS = ["amenity=restaurant", "amenity=cafe", "leisure=park"]

# Foursquare category ID → OSM tag (for backward compat with conversation_analysis.py)
_FSQ_CAT_TO_OSM = {
    "13065": "amenity=restaurant",
    "13376": "amenity=fast_food",
    "13035": "amenity=cafe",
    "13003": "amenity=bar",
    "13046": "amenity=pub",
    "16032": "leisure=park",
    "16034": "leisure=garden",
    "10056": "tourism=attraction",
    "10019": "tourism=museum",
    "10013": "tourism=gallery",
    "10000": "tourism=attraction",
    "10025": "amenity=cinema",
    "10046": "amenity=nightclub",
    "10032": "amenity=nightclub",
    "18000": "leisure=sports_centre",
    "18008": "leisure=fitness_centre",
    "17069": "shop=mall",
    "17000": "shop=mall",
}

_QUERY_TERM_MAP: dict[str, list[tuple[str, str, str | None, str | None]]] = {
    "restaurante":  [("amenity", "restaurant", None, None)],
    "restaurantes": [("amenity", "restaurant", None, None)],
    "lanchonete":   [("amenity", "fast_food", None, None)],
    "bar":          [("amenity", "bar", None, None), ("amenity", "pub", None, None)],
    "bares":        [("amenity", "bar", None, None), ("amenity", "pub", None, None)],
    "choperia":     [("amenity", "bar", None, None), ("craft", "brewery", None, None)],
    "café":         [("amenity", "cafe", None, None)],
    "cafeteria":    [("amenity", "cafe", None, None)],
    "churrascaria": [("amenity", "restaurant", "cuisine", "barbecue|churrasco")],
    "pizzaria":     [("amenity", "restaurant", "cuisine", "pizza")],
    "pizza":        [("amenity", "restaurant", "cuisine", "pizza"), ("amenity", "fast_food", "cuisine", "pizza")],
    "sushi":        [("amenity", "restaurant", "cuisine", "sushi|japanese")],
    "japonês":      [("amenity", "restaurant", "cuisine", "sushi|japanese")],
    "japonesa":     [("amenity", "restaurant", "cuisine", "sushi|japanese")],
    "italiano":     [("amenity", "restaurant", "cuisine", "italian")],
    "italiana":     [("amenity", "restaurant", "cuisine", "italian")],
    "hamburguer":   [("amenity", "fast_food", "cuisine", "burger"), ("amenity", "restaurant", "cuisine", "burger")],
    "hamburgueria": [("amenity", "fast_food", "cuisine", "burger"), ("amenity", "restaurant", "cuisine", "burger")],
    "balada":       [("amenity", "nightclub", None, None)],
    "boate":        [("amenity", "nightclub", None, None)],
    "parque":       [("leisure", "park", None, None), ("leisure", "garden", None, None)],
    "museu":        [("tourism", "museum", None, None)],
    "galeria":      [("tourism", "gallery", None, None)],
    "cinema":       [("amenity", "cinema", None, None)],
    "teatro":       [("amenity", "theatre", None, None)],
    "academia":     [("leisure", "fitness_centre", None, None), ("leisure", "sports_centre", None, None)],
    "sorveteria":   [("amenity", "ice_cream", None, None)],
    "padaria":      [("shop", "bakery", None, None), ("craft", "bakery", None, None)],
    "shopping":     [("shop", "mall", None, None)],
    "boliche":      [("leisure", "bowling_alley", None, None)],
}


def _osm_place_to_result(element, ref_lat, ref_lon):
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")
    if not lat or not lon:
        return None
    tags = element.get("tags", {})
    name = tags.get("name") or tags.get("name:pt") or tags.get("brand") or tags.get("official_name")
    if not name:
        return None
    address_parts = filter(None, [
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
        tags.get("addr:suburb") or tags.get("addr:city"),
    ])
    vicinity = ", ".join(address_parts) or tags.get("addr:city") or None
    distance = estimate_distance_km((ref_lat, ref_lon), (lat, lon))
    return {
        "name": name,
        "rating": None,
        "vicinity": vicinity,
        "distance_km": distance,
        "latitude": lat,
        "longitude": lon,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
    }


def _overpass_request(overpass_ql):
    from urllib.parse import quote_plus
    body = f"data={quote_plus(overpass_ql)}".encode("utf-8")
    return _http_json(
        "POST",
        "https://overpass-api.de/api/interpreter",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data=body,
    )


def _overpass_category_search(latitude, longitude, radius_meters, osm_tags, limit=50):
    filters = []
    for tag in osm_tags:
        key, _, value = tag.partition("=")
        for elem in ("node", "way"):
            filters.append(f'  {elem}["{key}"="{value}"](around:{radius_meters},{latitude},{longitude});')

    query = "[out:json][timeout:25];\n(\n" + "\n".join(filters) + f"\n);\nout center {limit};"
    response = _overpass_request(query)
    results = []
    for element in response.get("elements", []):
        result = _osm_place_to_result(element, latitude, longitude)
        if result:
            results.append(result)
    random.shuffle(results)
    return results[:limit]


def _overpass_name_search(latitude, longitude, radius_meters, query, limit=30):
    raw = query.lower().strip()
    tag_tuples = _QUERY_TERM_MAP.get(raw)

    if tag_tuples:
        # Fast path: indexed tag lookup for known PT terms
        filters = []
        for primary_key, primary_val, sec_key, sec_regex in tag_tuples:
            for elem in ("node", "way"):
                if sec_key and sec_regex:
                    filters.append(
                        f'  {elem}["{primary_key}"="{primary_val}"]["{sec_key}"~"{sec_regex}",i]'
                        f'(around:{radius_meters},{latitude},{longitude});'
                    )
                else:
                    filters.append(
                        f'  {elem}["{primary_key}"="{primary_val}"]'
                        f'(around:{radius_meters},{latitude},{longitude});'
                    )
        query_ql = "[out:json][timeout:25];\n(\n" + "\n".join(filters) + f"\n);\nout center {limit};"
        response = _overpass_request(query_ql)
    else:
        # Fallback: Nominatim free-text geocode search
        from urllib.parse import urlencode as _urlencode
        params = _urlencode({
            "q": raw,
            "format": "jsonv2",
            "limit": limit,
            "addressdetails": 1,
            "countrycodes": "br",
            "viewbox": f"{longitude - 0.5},{latitude + 0.5},{longitude + 0.5},{latitude - 0.5}",
            "bounded": 1,
        })
        nominatim_results = _http_json(
            "GET",
            f"https://nominatim.openstreetmap.org/search?{params}",
            headers={"Accept-Language": "pt-BR,pt;q=0.9"},
        )
        results = []
        seen = set()
        for item in nominatim_results:
            name = item.get("display_name", "").split(",")[0].strip()
            if not name or name in seen:
                continue
            seen.add(name)
            lat = float(item["lat"])
            lon = float(item["lon"])
            address = item.get("address", {})
            vicinity_parts = filter(None, [
                address.get("road"),
                address.get("suburb") or address.get("city_district") or address.get("city"),
            ])
            vicinity = ", ".join(vicinity_parts) or None
            distance = estimate_distance_km((latitude, longitude), (lat, lon))
            results.append({
                "name": name,
                "rating": None,
                "vicinity": vicinity,
                "distance_km": distance,
                "latitude": lat,
                "longitude": lon,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            })
        return results[:limit]

    results = []
    seen = set()
    for element in response.get("elements", []):
        result = _osm_place_to_result(element, latitude, longitude)
        if result and result["name"] not in seen:
            seen.add(result["name"])
            results.append(result)
    random.shuffle(results)
    return results[:limit]


def get_foursquare_suggestions(latitude, longitude, radius_meters, intent=None, category_ids=None, query=None):
    """Place search via OpenStreetMap Overpass API (gratuito, sem chave)."""
    if query:
        return _overpass_name_search(latitude, longitude, radius_meters, query)

    if category_ids:
        osm_tags = list(dict.fromkeys(
            _FSQ_CAT_TO_OSM[c] for c in category_ids if c in _FSQ_CAT_TO_OSM
        )) or _OSM_DEFAULT_TAGS
    else:
        osm_tags = _OSM_INTENT_TAGS.get(intent or "", _OSM_DEFAULT_TAGS)

    return _overpass_category_search(latitude, longitude, radius_meters, osm_tags)
def estimate_distance_km(origin, destination):
    earth_radius_km = 6371.0
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(earth_radius_km * c, 1)


def get_spotify_access_token():
    client_id = getattr(settings, "SPOTIFY_CLIENT_ID", "")
    client_secret = getattr(settings, "SPOTIFY_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise IntegrationError("Spotify nao configurado no backend.")

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    response = _http_json(
        "POST",
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body,
    )
    access_token = response.get("access_token")
    if not access_token:
        raise IntegrationError("Spotify nao retornou access token.")
    return access_token


def search_spotify_tracks(query, limit=8):
    if not query.strip():
        return []
    access_token = get_spotify_access_token()
    response = _http_json(
        "GET",
        f"https://api.spotify.com/v1/search?{urlencode({'q': query, 'type': 'track', 'limit': limit, 'market': 'BR'})}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    tracks = response.get("tracks", {}).get("items", [])
    results = []
    for track in tracks:
        images = track.get("album", {}).get("images", [])
        results.append({
            "id": track.get("id"),
            "name": track.get("name"),
            "artist": ", ".join(artist.get("name", "") for artist in track.get("artists", [])),
            "url": track.get("external_urls", {}).get("spotify"),
            "image_url": images[0].get("url") if images else "",
            "preview_url": track.get("preview_url"),
        })
    return results

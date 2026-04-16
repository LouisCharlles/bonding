import hashlib
import hmac
import json
import base64
from math import radians, sin, cos, sqrt, atan2
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class IntegrationError(RuntimeError):
    pass


def _http_json(method, url, headers=None, data=None):
    request = Request(
        url,
        method=method,
        headers=headers or {},
        data=data,
    )
    try:
        with urlopen(request) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise IntegrationError(f"{method} {url} falhou: {error.code} {body}") from error


def create_stripe_payment_intent(amount_brl_cents, customer_email, metadata=None):
    if not getattr(settings, "STRIPE_SECRET_KEY", ""):
        raise IntegrationError("STRIPE_SECRET_KEY nao configurada.")

    body = urlencode({
        "amount": amount_brl_cents,
        "currency": "brl",
        "automatic_payment_methods[enabled]": "true",
        "receipt_email": customer_email,
        **{
            f"metadata[{key}]": str(value)
            for key, value in (metadata or {}).items()
        },
    }).encode("utf-8")
    return _http_json(
        "POST",
        "https://api.stripe.com/v1/payment_intents",
        headers={
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=body,
    )


def verify_stripe_signature(payload, signature_header):
    secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise IntegrationError("STRIPE_WEBHOOK_SECRET nao configurada.")
    if not signature_header:
        raise IntegrationError("Stripe-Signature ausente.")

    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t")
    expected = parts.get("v1")
    if not timestamp or not expected:
        raise IntegrationError("Cabecalho Stripe-Signature invalido.")

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise IntegrationError("Assinatura do webhook invalida.")


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

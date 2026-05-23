import base64
import hashlib
import json
import urllib.request

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
from django.core.cache import cache


_GOOGLE_KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"
_CACHE_KEY = "google_ssv_public_keys"
_CACHE_TTL = 86400  # 24 hours


def get_google_public_keys() -> dict:
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    with urllib.request.urlopen(_GOOGLE_KEYS_URL, timeout=5) as resp:
        data = json.loads(resp.read())

    keys = {}
    for entry in data.get("keys", []):
        keys[str(entry["keyId"])] = entry["base64"]

    cache.set(_CACHE_KEY, keys, timeout=_CACHE_TTL)
    return keys


def verify_ssv_signature(query_string: str, key_id: str, signature_b64: str) -> bool:
    """
    Verifies Google SSV ECDSA-SHA256 signature.

    The signed content is the full query string (all params except 'signature'),
    sorted lexicographically and joined with '&', exactly as received from Google.
    """
    try:
        keys = get_google_public_keys()
        pem_b64 = keys.get(str(key_id))
        if not pem_b64:
            return False

        pem_bytes = base64.b64decode(pem_b64)
        public_key = load_pem_public_key(pem_bytes)

        sig_bytes = base64.urlsafe_b64decode(signature_b64 + "==")
        message_bytes = query_string.encode("utf-8")

        public_key.verify(sig_bytes, message_bytes, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, Exception):
        return False

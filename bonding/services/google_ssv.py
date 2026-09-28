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




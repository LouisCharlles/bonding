import pickle
from typing import Any, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core import checks
from django.core.signing import SignatureExpired
from django.db import models
from django.utils.encoding import force_bytes

FIELD_CACHE: dict[type[models.Field], type[models.Field]] = {}


class Expired:
    pass


def _derive_material(label: bytes, length: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=label,
        iterations=30000,
        backend=default_backend(),
    )
    source_key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    return kdf.derive(force_bytes(source_key))


class _FieldCipher:
    def __init__(self, key: Optional[bytes] = None) -> None:
        self._enc_key = key or _derive_material(b"bonding-field-encryption", 32)
        self._sig_key = _derive_material(b"bonding-field-signing", 32)

    def encrypt(self, value: bytes) -> bytes:
        import os
        import struct
        import time

        timestamp = int(time.time())
        iv = os.urandom(16)
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(value) + padder.finalize()
        cipher = Cipher(
            algorithms.AES(self._enc_key),
            modes.CBC(iv),
            backend=default_backend(),
        ).encryptor()
        ciphertext = cipher.update(padded) + cipher.finalize()
        payload = b"\x80" + struct.pack(">Q", timestamp) + iv + ciphertext
        signer = HMAC(self._sig_key, hashes.SHA256(), backend=default_backend())
        signer.update(payload)
        return payload + signer.finalize()

    def decrypt(self, value: bytes, ttl: Optional[int] = None) -> bytes:
        import struct
        import time

        if len(value) < 1 + 8 + 16 + 32:
            raise ValueError("Encrypted payload is too short.")

        payload = value[:-32]
        signature = value[-32:]
        signer = HMAC(self._sig_key, hashes.SHA256(), backend=default_backend())
        signer.update(payload)
        signer.verify(signature)

        version = payload[:1]
        if version != b"\x80":
            raise ValueError("Unsupported encrypted payload version.")

        timestamp = struct.unpack(">Q", payload[1:9])[0]
        if ttl is not None and abs(time.time() - timestamp) > ttl + 60:
            raise SignatureExpired("Encrypted payload expired.")

        iv = payload[9:25]
        ciphertext = payload[25:]
        decryptor = Cipher(
            algorithms.AES(self._enc_key),
            modes.CBC(iv),
            backend=default_backend(),
        ).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded) + unpadder.finalize()


def encrypt_object(value: Any) -> bytes:
    return _FieldCipher().encrypt(pickle.dumps(value))


def decrypt_object(value: bytes, ttl: Optional[int] = None) -> Any:
    return pickle.loads(_FieldCipher().decrypt(value, ttl))


class EncryptedMixin(models.Field):
    supported_lookups = ("isnull",)

    def __init__(self, *args, **kwargs):
        self.base_class = kwargs.pop("base_class", None)
        self.base_args = kwargs.pop("base_args", ())
        self.base_kwargs = kwargs.pop("base_kwargs", {})
        self.ttl = kwargs.pop("ttl", None)
        self._cipher = _FieldCipher()
        super().__init__(*args, **kwargs)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if getattr(self, "remote_field", None):
            errors.append(
                checks.Error(
                    "Base field for encrypted cannot be a related field.",
                    obj=self,
                    id="encrypted.E002",
                )
            )
        return errors

    def get_internal_type(self) -> str:
        return "BinaryField"

    def get_lookup(self, lookup_name):
        if lookup_name not in self.supported_lookups:
            return None
        return super().get_lookup(lookup_name)

    def get_transform(self, lookup_name):
        if lookup_name not in self.supported_lookups:
            return None
        return super().get_transform(lookup_name)

    def get_db_prep_value(self, value: Any, connection, prepared: bool = False):
        value = models.Field.get_db_prep_value(self, value, connection, prepared)
        if value is None:
            return value
        encrypted = encrypt_object(value)
        return connection.Database.Binary(encrypted)

    get_db_prep_save = models.Field.get_db_prep_save

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return value
        return self._load(force_bytes(value))

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, (dict, list, tuple, str, int, float, bool)):
            return value
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, (bytes, bytearray)):
            return self._load(bytes(value))
        return value

    def _load(self, value: bytes):
        try:
            return decrypt_object(value, self.ttl)
        except SignatureExpired:
            return Expired()

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.base_class is not None:
            path = "bonding.security_crypto.encrypt"
            args = [self.base_class(*self.base_args, **self.base_kwargs)]
            kwargs = {}
            if self.ttl is not None:
                kwargs["ttl"] = self.ttl
        return name, path, args, kwargs


class EncryptedJSONField(EncryptedMixin, models.JSONField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_class", models.JSONField)
        kwargs.setdefault("base_args", args)
        kwargs.setdefault("base_kwargs", kwargs.copy())
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = models.JSONField.deconstruct(self)
        path = "bonding.security_crypto.EncryptedJSONField"
        return name, path, args, kwargs


def encrypt(base_field, ttl: Optional[int] = None):
    base_class = type(base_field)
    _, _, args, kwargs = base_field.deconstruct()
    encrypted_class = FIELD_CACHE.get(base_class)
    if encrypted_class is None:
        encrypted_class = type(
            f"Encrypted{base_class.__name__}",
            (EncryptedMixin, base_class),
            {},
        )
        encrypted_class.__module__ = __name__
        FIELD_CACHE[base_class] = encrypted_class
        globals()[encrypted_class.__name__] = encrypted_class

    return encrypted_class(
        *args,
        ttl=ttl,
        base_class=base_class,
        base_args=args,
        base_kwargs=kwargs,
        **kwargs,
    )

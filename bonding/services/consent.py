import hashlib
import hmac
import json

from django.db import transaction
from django.utils import timezone

from ..models import ConsentRecord
from ..security_crypto import _derive_material

GENESIS_HASH = "0" * 64


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _signing_key() -> bytes:
    return _derive_material(b"bonding-consent-chain", 32)


def _canonical_payload(
    *,
    user_id,
    document_version_id,
    consent_type,
    action,
    granted_at,
    ip_address,
    user_agent,
    metadata,
) -> str:
    return json.dumps(
        {
            "user_id": user_id,
            "document_version_id": document_version_id,
            "consent_type": consent_type,
            "action": action,
            "granted_at": granted_at.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata,
        },
        sort_keys=True,
        default=str,
    )


def record_consent(
    *,
    user,
    consent_type,
    request=None,
    document_version=None,
    action=ConsentRecord.ACTION_GRANTED,
    metadata=None,
    ip_address=None,
    user_agent="",
):
    """Unica porta de entrada para gravar um ConsentRecord. Nunca instanciar
    o model diretamente fora daqui — a integridade da cadeia depende disso."""
    metadata = metadata or {}
    granted_at = timezone.now()

    if request is not None:
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    with transaction.atomic():
        last = ConsentRecord.objects.select_for_update().order_by("-id").first()
        prev_hash = last.hmac_signature if last else GENESIS_HASH

        payload = _canonical_payload(
            user_id=user.id,
            document_version_id=document_version.id if document_version else None,
            consent_type=consent_type,
            action=action,
            granted_at=granted_at,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
        content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        signature = hmac.new(
            _signing_key(),
            (content_hash + prev_hash).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return ConsentRecord.objects.create(
            user=user,
            document_version=document_version,
            consent_type=consent_type,
            action=action,
            granted_at=granted_at,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            prev_hash=prev_hash,
            content_hash=content_hash,
            hmac_signature=signature,
        )


def verify_chain_integrity(from_id=None):
    """Recalcula a cadeia inteira (ou a partir de from_id) e retorna a lista
    de inconsistencias encontradas. Lista vazia = cadeia integra."""
    qs = ConsentRecord.objects.order_by("id")
    expected_prev = GENESIS_HASH

    if from_id is not None:
        qs = qs.filter(id__gte=from_id)
        anchor = ConsentRecord.objects.filter(id__lt=from_id).order_by("-id").first()
        expected_prev = anchor.hmac_signature if anchor else GENESIS_HASH

    issues = []
    for record in qs:
        payload = _canonical_payload(
            user_id=record.user_id,
            document_version_id=record.document_version_id,
            consent_type=record.consent_type,
            action=record.action,
            granted_at=record.granted_at,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            metadata=record.metadata,
        )
        expected_content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        expected_signature = hmac.new(
            _signing_key(),
            (expected_content_hash + expected_prev).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if record.prev_hash != expected_prev:
            issues.append({"id": record.id, "error": "prev_hash_mismatch"})
        if record.content_hash != expected_content_hash:
            issues.append({"id": record.id, "error": "content_hash_mismatch"})
        if record.hmac_signature != expected_signature:
            issues.append({"id": record.id, "error": "signature_mismatch"})

        expected_prev = record.hmac_signature

    return issues

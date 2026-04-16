from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .external_integrations import IntegrationError


SIMILARITY_APPROVAL_THRESHOLD = 90
SELFIE_MIN_BRIGHTNESS = 35
SELFIE_MIN_SHARPNESS = 40


@dataclass
class VerificationResult:
    approved: bool
    score: float
    rejection_reason: str
    provider_payload: dict
    brightness_score: float | None = None
    face_detected: bool = False
    accessories_detected: bool = False


def _read_field_bytes(field_file) -> bytes:
    if not field_file:
        raise IntegrationError("Arquivo de imagem ausente para verificacao.")

    field_file.open("rb")
    try:
        return field_file.read()
    finally:
        field_file.close()


def compare_profile_selfie(profile, selfie) -> VerificationResult:
    provider = getattr(settings, "VERIFICATION_PROVIDER", "aws_rekognition")
    if provider != "aws_rekognition":
        raise IntegrationError("Provider de verificacao nao suportado.")
    if not getattr(settings, "AWS_REKOGNITION_ENABLED", False):
        raise IntegrationError("AWS_REKOGNITION_ENABLED nao configurado para uso real.")

    try:
        import boto3
    except ImportError as error:
        raise IntegrationError("boto3 nao instalado no backend para usar AWS Rekognition.") from error

    profile_photos = list(profile.photos.all()[:2])
    if len(profile_photos) < 2:
        raise IntegrationError("O perfil precisa de pelo menos duas fotos para verificacao.")

    rekognition = boto3.client("rekognition", region_name=getattr(settings, "AWS_DEFAULT_REGION", None))
    selfie_bytes = _read_field_bytes(selfie.image)

    try:
        face_detection = rekognition.detect_faces(
            Image={"Bytes": selfie_bytes},
            Attributes=["ALL"],
        )
    except Exception as error:
        raise IntegrationError(f"Falha ao analisar a selfie no Rekognition: {error}") from error

    face_details = face_detection.get("FaceDetails", [])
    if not face_details:
        return VerificationResult(
            approved=False,
            score=0,
            rejection_reason="Nenhum rosto detectado na selfie.",
            provider_payload={"face_detection": face_detection},
            face_detected=False,
        )

    primary_face = face_details[0]
    quality = primary_face.get("Quality", {})
    brightness = float(quality.get("Brightness") or 0)
    sharpness = float(quality.get("Sharpness") or 0)
    accessories_detected = bool(
        primary_face.get("Sunglasses", {}).get("Value")
        or primary_face.get("FaceOccluded", {}).get("Value")
    )

    if brightness < SELFIE_MIN_BRIGHTNESS:
        return VerificationResult(
            approved=False,
            score=0,
            rejection_reason="Ambiente muito escuro para verificar o rosto com segurança.",
            provider_payload={"face_detection": face_detection},
            brightness_score=brightness,
            face_detected=True,
            accessories_detected=accessories_detected,
        )

    if sharpness < SELFIE_MIN_SHARPNESS:
        return VerificationResult(
            approved=False,
            score=0,
            rejection_reason="A selfie está desfocada demais para a comparação facial.",
            provider_payload={"face_detection": face_detection},
            brightness_score=brightness,
            face_detected=True,
            accessories_detected=accessories_detected,
        )

    if accessories_detected:
        return VerificationResult(
            approved=False,
            score=0,
            rejection_reason="Remova acessórios que escondam o rosto e envie outra selfie.",
            provider_payload={"face_detection": face_detection},
            brightness_score=brightness,
            face_detected=True,
            accessories_detected=True,
        )

    comparisons = []
    best_similarity = 0.0

    for photo in profile_photos:
        try:
            target_bytes = _read_field_bytes(photo.image)
            comparison = rekognition.compare_faces(
                SourceImage={"Bytes": selfie_bytes},
                TargetImage={"Bytes": target_bytes},
                SimilarityThreshold=80,
                QualityFilter="AUTO",
            )
        except Exception as error:
            raise IntegrationError(f"Falha ao comparar a selfie com as fotos do perfil: {error}") from error

        similarities = [float(match.get("Similarity") or 0) for match in comparison.get("FaceMatches", [])]
        photo_best = max(similarities, default=0.0)
        best_similarity = max(best_similarity, photo_best)
        comparisons.append({
            "photo_id": photo.id,
            "best_similarity": photo_best,
            "raw": comparison,
        })

    provider_payload = {
        "face_detection": face_detection,
        "comparisons": comparisons,
        "thresholds": {
            "similarity_approval": SIMILARITY_APPROVAL_THRESHOLD,
            "min_brightness": SELFIE_MIN_BRIGHTNESS,
            "min_sharpness": SELFIE_MIN_SHARPNESS,
        },
    }

    approved = best_similarity >= SIMILARITY_APPROVAL_THRESHOLD
    return VerificationResult(
        approved=approved,
        score=round(best_similarity / 100, 4),
        rejection_reason="" if approved else "A selfie nao atingiu semelhança suficiente com as fotos do perfil.",
        provider_payload=provider_payload,
        brightness_score=brightness,
        face_detected=True,
        accessories_detected=accessories_detected,
    )

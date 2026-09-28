import uuid

from django.db import transaction

from ..models import ConsentRecord, Photo, Profile
from .consent import record_consent


def deactivate_account(user, request=None):
    """Congela a conta: bloqueia login/autenticacao (is_active=False) sem
    apagar ou anonimizar nenhum dado. Reversivel (reativacao e um processo
    manual/administrativo, fora do escopo desta acao self-service)."""
    with transaction.atomic():
        user.is_active = False
        user.save(update_fields=["is_active"])
        record_consent(user=user, consent_type=ConsentRecord.ACCOUNT_DEACTIVATION, request=request)
    return user


def reactivate_account(user, request=None):
    """Reativacao self-service: chamada quando um usuario que desativou a
    propria conta (deactivate_account) tenta logar de novo com o mesmo
    e-mail e senha corretos. So se aplica a contas DESATIVADAS — contas
    excluidas (delete_account) trocam o e-mail por um placeholder, entao o
    e-mail original nunca mais encontra correspondencia no login."""
    with transaction.atomic():
        user.is_active = True
        user.save(update_fields=["is_active"])
        record_consent(user=user, consent_type=ConsentRecord.ACCOUNT_REACTIVATION, request=request)
    return user


def delete_account(user, request=None):
    """Exclusao self-service: anonimiza dados identificaveis e apaga midia
    de storage, mas NAO apaga o User nem o ConsentRecord do usuario — o
    proprio ConsentRecord.user usa on_delete=PROTECT e e a prova de que o
    direito de exclusao (LGPD Art. 18) foi exercido e honrado. Subscription/
    WalletLedger tambem permanecem intactos (retencao fiscal), pois o User
    em si nunca e removido, apenas desativado e esvaziado de dados pessoais."""
    with transaction.atomic():
        record_consent(user=user, consent_type=ConsentRecord.ACCOUNT_DELETION, request=request)

        profile = getattr(user, "profile", None)
        if profile is not None:
            for photo in Photo.objects.filter(profile=profile):
                photo.image.delete(save=False)
            Photo.objects.filter(profile=profile).delete()

            for attempt in profile.verification_attempts.all():
                selfie = getattr(attempt, "selfie", None)
                if selfie is not None:
                    selfie.image.delete(save=False)
            profile.verification_attempts.all().delete()

            profile.name = "Usuario removido"
            profile.bio = ""
            profile.occupation = ""
            profile.education = ""
            profile.course = ""
            profile.gender = Profile.GENDER_OTHER
            profile.sexual_orientation = Profile.ORIENTATION_OTHER
            profile.relationship_intent = Profile.INTENT_EXPLORING
            profile.spotify_track_id = ""
            profile.spotify_track_name = ""
            profile.spotify_artist_name = ""
            profile.spotify_track_url = ""
            profile.spotify_album_image_url = ""
            profile.spotify_preview_url = ""
            profile.location = None
            profile.is_verified = False
            profile.verification_status = Profile.VERIFICATION_PENDING
            profile.is_invisible_mode = True
            profile.interests.clear()
            profile.preferences.clear()
            profile.save()

        user.is_active = False
        user.set_unusable_password()
        user.email = f"deleted-user-{user.id}-{uuid.uuid4().hex[:8]}@deleted.bonding.local"
        user.save(update_fields=["is_active", "password", "email"])

    return user

from datetime import timedelta, datetime

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from bonding.models import VerificationToken


def send_verification_email(user):
    token, _ = VerificationToken.objects.get_or_create(user=user)
    token.expires_at = datetime.now() + timedelta(minutes=30)
    token.save(update_fields=["expires_at"])

    verify_path = reverse("verify-email", args=[user.id, token.token])
    verify_url = f"{settings.BACKEND_URL.rstrip('/')}{verify_path}"

    email_subject = "Confirme seu e-mail para acesso"
    email_body = render_to_string(
        "emails/verification_email.html",
        {
            "user": user,
            "verify_url": verify_url,
        },
    )

    email = EmailMessage(
        email_subject,
        email_body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.content_subtype = "html"
    email.send()

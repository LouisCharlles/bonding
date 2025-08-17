import uuid
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from datetime import timedelta, datetime
from bonding.models import VerificationToken

def send_verification_email(user):
    #Tenta criar ou obter token de autenticação
    token, created = VerificationToken.objects.get_or_create(user=user)
    token.expires_at = datetime.now() + timedelta(minutes=30)
    token.save()

    #Cria o link de verificação
    #Substitua 'http://seu-dominio.com' pelo seu domínio em produção
    # A view 'verify-email' será criada no próximo passo
    verify_url = f"http:seu-dominio.com/api/verify-email/{user.id}/{token.token}/"

    email_subject = 'Confirme seu e-email para acesso'
    email_body = render_to_string('emails/verification_email.html',{
        'user':user,
        'verify_url':verify_url
    })

    email = EmailMessage(
        email_subject,
        email_body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email]
    )
    email.content_subtype = "html"
    email.send()

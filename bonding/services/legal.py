from django.db import transaction

from ..models import LegalDocumentVersion


def publish_document_version(
    *, document_type, version_label, content, effective_date, dpo_contact_snapshot=""
):
    """Publica uma nova versao de um documento legal, tornando-a a corrente
    e desativando a versao anterior daquele tipo na mesma transacao."""
    with transaction.atomic():
        LegalDocumentVersion.objects.filter(
            document_type=document_type, is_current=True
        ).update(is_current=False)

        return LegalDocumentVersion.objects.create(
            document_type=document_type,
            version_label=version_label,
            content=content,
            effective_date=effective_date,
            dpo_contact_snapshot=dpo_contact_snapshot,
            is_current=True,
        )

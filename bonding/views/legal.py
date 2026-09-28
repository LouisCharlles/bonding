from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ConsentRecord, LegalDocumentVersion
from ..serializers import ConsentRecordSerializer, LegalDocumentVersionSerializer
from ..services.consent import record_consent


class LegalDocumentCurrentView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        documents = LegalDocumentVersion.objects.filter(is_current=True)
        serializer = LegalDocumentVersionSerializer(documents, many=True)
        return Response(serializer.data)


class ConsentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        consent_type = request.data.get("consent_type")
        if consent_type not in dict(ConsentRecord.consent_type_choices):
            return Response(
                {"detail": "consent_type invalido."}, status=status.HTTP_400_BAD_REQUEST
            )

        document_version = None
        document_version_id = request.data.get("document_version_id")
        if document_version_id:
            document_version = get_object_or_404(LegalDocumentVersion, pk=document_version_id)

        record = record_consent(
            user=request.user,
            consent_type=consent_type,
            request=request,
            document_version=document_version,
            metadata=request.data.get("metadata") or {},
        )
        return Response(ConsentRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class ConsentMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = ConsentRecord.objects.filter(user=request.user).order_by(
            "consent_type", "-granted_at"
        )
        latest_by_type = {}
        for record in records:
            latest_by_type.setdefault(record.consent_type, record)

        current_docs = {
            doc.document_type: doc
            for doc in LegalDocumentVersion.objects.filter(is_current=True)
        }

        result = []
        for consent_type, record in latest_by_type.items():
            is_up_to_date = record.action == ConsentRecord.ACTION_GRANTED
            if is_up_to_date and record.document_version_id:
                current_doc = current_docs.get(record.document_version.document_type)
                is_up_to_date = bool(current_doc) and record.document_version_id == current_doc.id
            result.append(
                {
                    "consent_type": consent_type,
                    "action": record.action,
                    "granted_at": record.granted_at,
                    "is_up_to_date": is_up_to_date,
                }
            )

        return Response(result)

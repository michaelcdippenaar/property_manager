"""
Legal API views.

Endpoints:
  GET  /api/v1/legal/documents/current/  — list all current legal documents
  GET  /api/v1/legal/pending/            — documents user must (re-)accept
  POST /api/v1/legal/consent/            — record user acceptance of a document
  GET  /api/v1/legal/consent/            — list all consents for current user
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LegalDocument, UserConsent
from .serializers import LegalDocumentSerializer, UserConsentSerializer, PendingConsentSerializer


class CurrentDocumentsView(APIView):
    """Public — returns all current legal documents (so front-end can link to them)."""
    permission_classes = [AllowAny]

    def get(self, request):
        docs = LegalDocument.objects.filter(is_current=True)
        return Response(LegalDocumentSerializer(docs, many=True).data)


class PendingConsentsView(APIView):
    """
    Authenticated — returns documents that require re-acknowledgement
    and have not yet been accepted by the current user.

    Front-end calls this after login to decide whether to show an acceptance gate.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending = UserConsent.pending_for_user(request.user)
        return Response(PendingConsentSerializer(pending, many=True).data)


class UserConsentView(APIView):
    """
    GET  — list all consents recorded for the current user.
    POST — record acceptance of a specific document version.

    POST body: { "document": <document_id> }
    Idempotent: posting the same document twice returns 200 with the existing record.
    New consent returns 201.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        consents = UserConsent.objects.filter(user=request.user).select_related("document")
        return Response(UserConsentSerializer(consents, many=True).data)

    def post(self, request):
        serializer = UserConsentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        consent = serializer.save()
        # 201 if a new row was created; 200 if the same version was already recorded (idempotent).
        response_status = status.HTTP_201_CREATED if getattr(consent, "_created", False) else status.HTTP_200_OK
        return Response(UserConsentSerializer(consent).data, status=response_status)

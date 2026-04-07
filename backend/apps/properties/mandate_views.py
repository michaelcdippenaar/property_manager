"""
Rental Mandate Views
====================
Provides CRUD for RentalMandate plus the `send-for-signing` action that
generates the mandate PDF and kicks off the native e-signing flow.
"""
import hashlib
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAgentOrAdmin
from apps.esigning.models import ESigningSubmission
from apps.esigning.views import _auto_send_signing_links
from apps.properties.access import get_accessible_property_ids

from .mandate_serializers import RentalMandateSerializer
from .mandate_services import build_mandate_signers, generate_mandate_html
from .models import RentalMandate

logger = logging.getLogger(__name__)


class RentalMandateViewSet(viewsets.ModelViewSet):
    """
    CRUD for rental mandates, scoped to properties accessible by the requesting user.

    Endpoints:
      GET    /api/v1/properties/mandates/?property={id}
      POST   /api/v1/properties/mandates/
      GET    /api/v1/properties/mandates/{id}/
      PATCH  /api/v1/properties/mandates/{id}/
      DELETE /api/v1/properties/mandates/{id}/
      POST   /api/v1/properties/mandates/{id}/send-for-signing/
    """

    serializer_class   = RentalMandateSerializer
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get_queryset(self):
        prop_ids = get_accessible_property_ids(self.request.user)
        qs = RentalMandate.objects.filter(
            property_id__in=prop_ids
        ).select_related("property", "landlord", "esigning_submission")

        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(property_id=property_id)

        return qs

    def perform_create(self, serializer):
        mandate = serializer.save(created_by=self.request.user)
        # Auto-link landlord from current PropertyOwnership if not supplied
        if not mandate.landlord_id:
            ownership = mandate.property.ownerships.filter(is_current=True).select_related("landlord").first()
            if ownership and ownership.landlord_id:
                mandate.landlord = ownership.landlord
                mandate.save(update_fields=["landlord"])

    @action(detail=True, methods=["post"], url_path="send-for-signing")
    def send_for_signing(self, request, pk=None):
        """
        Generate the mandate HTML document, create a native ESigningSubmission,
        and email signing links to the owner (first) and agent (second).
        """
        mandate = self.get_object()

        if mandate.status != RentalMandate.Status.DRAFT:
            return Response(
                {"detail": f"Cannot send: mandate is already '{mandate.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve signers — validates owner email early
        signers = build_mandate_signers(mandate, request.user)
        owner_signer = signers[0]
        if not owner_signer.get("email"):
            return Response(
                {"detail": "Owner email address is required before sending. "
                           "Update the landlord or property ownership record first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate the mandate HTML document
        try:
            html = generate_mandate_html(mandate, agent_user=request.user)
        except Exception as exc:
            logger.exception("Mandate HTML generation failed for mandate %s", mandate.pk)
            return Response(
                {"detail": f"Document generation failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        doc_hash = hashlib.sha256(html.encode()).hexdigest()

        # Build signer records (mirroring services.create_native_submission pattern)
        signer_records = []
        for idx, s in enumerate(signers):
            signer_records.append({
                "id":     idx + 1,
                "name":   s["name"],
                "email":  s["email"],
                "phone":  s.get("phone", ""),
                "role":   s["role"],
                "order":  s["order"],
                "status": "pending",
            })

        # Create the ESigningSubmission (lease=None, mandate=mandate)
        try:
            submission = ESigningSubmission.objects.create(
                lease=None,
                mandate=mandate,
                signing_backend=ESigningSubmission.SigningBackend.NATIVE,
                signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
                status=ESigningSubmission.Status.PENDING,
                signers=signer_records,
                document_html=html,
                document_hash=doc_hash,
                created_by=request.user,
            )
        except Exception as exc:
            logger.exception("Failed to create ESigningSubmission for mandate %s", mandate.pk)
            return Response(
                {"detail": f"Failed to create signing submission: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Link and update mandate status
        mandate.esigning_submission = submission
        mandate.status = RentalMandate.Status.SENT
        mandate.save(update_fields=["esigning_submission", "status", "updated_at"])

        # Send signing link emails
        try:
            _auto_send_signing_links(submission, signers, request)
        except Exception:
            logger.exception(
                "Failed to send signing link emails for mandate submission %s", submission.pk
            )
            # Non-fatal — mandate and submission are created; agent can resend manually

        return Response(
            RentalMandateSerializer(mandate, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

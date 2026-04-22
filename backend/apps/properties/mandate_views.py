"""
Rental Mandate Views
====================
Provides CRUD for RentalMandate plus these actions:
  - `send-for-signing` — generates the mandate PDF and kicks off the native e-signing flow
  - `terminate`        — terminates an active mandate (notice period + active-lease check)
  - `renew`            — clones a mandate for renewal, linking it to its predecessor
"""
import hashlib
import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAgentOrAdmin
from apps.esigning.models import ESigningSubmission
from apps.esigning.views import _auto_send_signing_links
from apps.properties.access import get_accessible_property_ids

from .mandate_serializers import MandateRenewSerializer, RentalMandateSerializer
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

    # ------------------------------------------------------------------ #
    # terminate                                                            #
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="terminate")
    def terminate(self, request, pk=None):
        """
        Terminate an active mandate.

        Rules enforced:
          - Only `active` mandates may be terminated.
          - If the property has a currently active lease, termination is
            blocked unless `override_active_lease=true` is supplied.
          - `reason` (str) is required to record the written notice.

        POST body:
          {
            "reason": "...",
            "override_active_lease": false   // optional, default false
          }
        """
        mandate = self.get_object()

        if mandate.status != RentalMandate.Status.ACTIVE:
            return Response(
                {"detail": f"Only active mandates can be terminated. Current status: '{mandate.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response(
                {"detail": "A written termination reason is required (notice_period_days="
                           f"{mandate.notice_period_days})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        override = bool(request.data.get("override_active_lease", False))

        # Active-lease guard
        has_active_lease = mandate.property.units.filter(
            leases__status="active"
        ).exists()
        if has_active_lease and not override:
            return Response(
                {"detail": "This property has an active lease. Terminating the mandate while "
                           "tenants are in occupation may create legal exposure. "
                           "Pass override_active_lease=true to proceed."},
                status=status.HTTP_409_CONFLICT,
            )

        mandate.status             = RentalMandate.Status.TERMINATED
        mandate.terminated_at      = timezone.now()
        mandate.terminated_reason  = reason
        mandate.save(update_fields=["status", "terminated_at", "terminated_reason", "updated_at"])

        return Response(
            RentalMandateSerializer(mandate, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # renew                                                                #
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="renew")
    def renew(self, request, pk=None):
        """
        Clone the mandate for renewal.

        Creates a new draft mandate for the same property and landlord,
        copying all terms.  The new mandate's `previous_mandate` FK points
        back to this one, preserving the audit chain.

        The source mandate must be `active`, `expired`, or `terminated`.

        Optional POST body keys (override cloned defaults):
          start_date, end_date, commission_rate, commission_period,
          notice_period_days, maintenance_threshold, notes
        """
        mandate = self.get_object()

        if mandate.status not in (
            RentalMandate.Status.ACTIVE,
            RentalMandate.Status.EXPIRED,
            RentalMandate.Status.TERMINATED,
        ):
            return Response(
                {"detail": f"Cannot renew a mandate in status '{mandate.status}'. "
                           "Only active, expired, or terminated mandates may be renewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        renew_ser = MandateRenewSerializer(data=request.data or {})
        if not renew_ser.is_valid():
            return Response(renew_ser.errors, status=status.HTTP_400_BAD_REQUEST)

        overrides = renew_ser.validated_data

        new_mandate = RentalMandate.objects.create(
            property              = mandate.property,
            landlord              = mandate.landlord,
            mandate_type          = mandate.mandate_type,
            exclusivity           = mandate.exclusivity,
            commission_rate       = overrides.get("commission_rate",       mandate.commission_rate),
            commission_period     = overrides.get("commission_period",     mandate.commission_period),
            start_date            = overrides.get("start_date",            mandate.start_date),
            end_date              = overrides.get("end_date",              mandate.end_date),
            notice_period_days    = overrides.get("notice_period_days",    mandate.notice_period_days),
            maintenance_threshold = overrides.get("maintenance_threshold", mandate.maintenance_threshold),
            notes                 = overrides.get("notes", ""),
            status                = RentalMandate.Status.DRAFT,
            previous_mandate      = mandate,
            created_by            = request.user,
        )

        return Response(
            RentalMandateSerializer(new_mandate, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.the_volt.encryption.utils import generate_api_key, generate_otp, hash_otp
from apps.the_volt.owners.models import VaultOwner
from .auth import VoltApiKeyAuthentication
from .checkout import CheckoutService, CheckoutError
from .models import (
    DataSubscriber,
    DataRequest,
    DataRequestApprovalLink,
    RequestStatus,
    DeliveryMethod,
)
from .serializers import (
    DataSubscriberSerializer,
    DataRequestSerializer,
    ApprovalInfoSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscriber-facing (X-Volt-API-Key auth)
# ---------------------------------------------------------------------------

class DataRequestCreateView(APIView):
    """POST /gateway/request/ — subscriber requests access to a vault owner's data.

    Body:
    {
        "vault_owner_email": "owner@example.com",
        "requested_entity_types": ["personal", "company"],
        "requested_fields": {"personal": ["id_number", "address"], "company": ["reg_number"]},
        "requested_document_types": ["id_document", "proof_of_address"],
        "purpose": "FICA verification for loan application"
    }
    """

    authentication_classes = [VoltApiKeyAuthentication]
    permission_classes = []  # API key auth via VoltApiKeyAuthentication

    def post(self, request):
        subscriber = request.auth
        if not subscriber:
            return Response({"detail": "Invalid API key."}, status=status.HTTP_401_UNAUTHORIZED)

        vault_owner_email = request.data.get("vault_owner_email", "").strip()
        if not vault_owner_email:
            return Response({"detail": "vault_owner_email is required."}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=vault_owner_email)
        except User.DoesNotExist:
            return Response({"detail": "Vault owner not found."}, status=status.HTTP_404_NOT_FOUND)

        vault = VaultOwner.get_or_create_for_user(user)

        data_request = DataRequest.objects.create(
            subscriber=subscriber,
            vault=vault,
            requested_entity_types=request.data.get("requested_entity_types", []),
            requested_fields=request.data.get("requested_fields", {}),
            requested_document_types=request.data.get("requested_document_types", []),
            purpose=request.data.get("purpose", ""),
        )

        # Generate approval link + OTP, send via SMS
        otp_plaintext, otp_hash = generate_otp()
        approval_link = DataRequestApprovalLink.objects.create(
            request=data_request,
            otp_hash=otp_hash,
            expires_at=data_request.expires_at,
        )
        self._send_otp_sms(user, otp_plaintext, approval_link.token, data_request)

        return Response({
            "access_token": str(data_request.access_token),
            "status": data_request.status,
            "expires_at": data_request.expires_at,
            "message": "Request created. Owner has been notified via SMS.",
        }, status=status.HTTP_201_CREATED)

    def _send_otp_sms(self, user, otp_plaintext, token, data_request):
        """Send approval URL + OTP to the vault owner via SMS."""
        try:
            from django.conf import settings
            base_url = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "https://app.klikk.co.za")
            approval_url = f"{base_url}/vault/approve/{token}/"
            message = (
                f"Klikk Vault: {data_request.subscriber.org_name} requests access to your data.\n"
                f"OTP: {otp_plaintext}\n"
                f"Review: {approval_url}\n"
                f"This link expires in 48 hours."
            )
            if user.phone:
                from core.notifications import send_sms
                send_sms(user.phone, message)
        except Exception:
            logger.exception("Volt: failed to send OTP SMS to user_id=%s", user.pk)


class DataCheckoutView(APIView):
    """POST /gateway/checkout/ — subscriber retrieves approved vault data.

    Body:
    {
        "access_token": "<uuid>",
        "delivery_method": "rest"
    }
    """

    authentication_classes = [VoltApiKeyAuthentication]
    permission_classes = []

    def post(self, request):
        subscriber = request.auth
        if not subscriber:
            return Response({"detail": "Invalid API key."}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = request.data.get("access_token", "").strip()
        if not access_token:
            return Response({"detail": "access_token is required."}, status=400)

        try:
            data_request = DataRequest.objects.select_related(
                "vault__user", "subscriber"
            ).get(access_token=access_token, subscriber=subscriber)
        except DataRequest.DoesNotExist:
            return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        delivery_method = request.data.get("delivery_method", DeliveryMethod.REST)
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))

        try:
            service = CheckoutService(data_request, delivery_method=delivery_method, ip_address=ip_address)
            result = service.execute()
        except CheckoutError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class DataCheckoutStatusView(APIView):
    """GET /gateway/requests/{token}/status/ — poll request status (subscriber-facing)."""

    authentication_classes = [VoltApiKeyAuthentication]
    permission_classes = []

    def get(self, request, token):
        subscriber = request.auth
        if not subscriber:
            return Response({"detail": "Invalid API key."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            data_request = DataRequest.objects.get(access_token=token, subscriber=subscriber)
        except DataRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "access_token": str(data_request.access_token),
            "status": data_request.status,
            "is_expired": data_request.is_expired,
            "expires_at": data_request.expires_at,
        })


# ---------------------------------------------------------------------------
# Owner-facing (JWT auth)
# ---------------------------------------------------------------------------

class DataRequestListView(APIView):
    """GET /gateway/requests/ — list incoming data requests for the owner's vault."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        vault = VaultOwner.get_or_create_for_user(request.user)
        requests_qs = DataRequest.objects.filter(
            vault=vault,
        ).select_related("subscriber").order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            requests_qs = requests_qs.filter(status=status_filter)

        return Response(DataRequestSerializer(requests_qs, many=True).data)


class DataRequestApproveView(APIView):
    """POST /gateway/requests/{token}/approve/ — owner approves a request (JWT auth)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        vault = VaultOwner.get_or_create_for_user(request.user)
        try:
            data_request = DataRequest.objects.get(access_token=token, vault=vault)
        except DataRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if data_request.status != RequestStatus.PENDING:
            return Response({"detail": f"Request is already {data_request.status}."}, status=400)
        if data_request.is_expired:
            DataRequest.objects.filter(pk=data_request.pk).update(status=RequestStatus.EXPIRED)
            return Response({"detail": "Request has expired."}, status=400)

        DataRequest.objects.filter(pk=data_request.pk).update(
            status=RequestStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now(),
        )
        return Response({"status": RequestStatus.APPROVED, "access_token": str(token)})


class DataRequestDenyView(APIView):
    """POST /gateway/requests/{token}/deny/ — owner denies a request (JWT auth)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        vault = VaultOwner.get_or_create_for_user(request.user)
        try:
            data_request = DataRequest.objects.get(access_token=token, vault=vault)
        except DataRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if data_request.status != RequestStatus.PENDING:
            return Response({"detail": f"Request is already {data_request.status}."}, status=400)

        DataRequest.objects.filter(pk=data_request.pk).update(status=RequestStatus.DENIED)
        return Response({"status": RequestStatus.DENIED, "access_token": str(token)})


# ---------------------------------------------------------------------------
# Public approval (UUID token + OTP — no auth required)
# ---------------------------------------------------------------------------

class DataRequestApprovalInfoView(APIView):
    """GET /gateway/requests/{token}/approval-info/ — returns request details for the approval page.

    No OTP required to VIEW (owner needs to see what they're approving before entering OTP).
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        try:
            link = DataRequestApprovalLink.objects.select_related(
                "request__subscriber", "request__vault__user"
            ).get(token=token)
        except DataRequestApprovalLink.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if link.is_expired:
            return Response({"detail": "This approval link has expired."}, status=400)
        if link.is_used:
            return Response({"detail": "This approval link has already been used."}, status=400)

        return Response(ApprovalInfoSerializer(link.request).data)


class DataRequestApprovePublicView(APIView):
    """POST /gateway/requests/{token}/approve-public/ — owner approves/denies via OTP.

    Body:
    {
        "otp": "123456",
        "decision": "approve" | "deny"
    }

    No JWT required — UUID token + OTP is the auth.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request, token):
        try:
            link = DataRequestApprovalLink.objects.select_related(
                "request__vault__user"
            ).get(token=token)
        except DataRequestApprovalLink.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if link.is_expired:
            return Response({"detail": "This approval link has expired."}, status=400)
        if link.is_used:
            return Response({"detail": "This approval link has already been used."}, status=400)
        if link.is_locked:
            return Response({"detail": "Too many incorrect OTP attempts. Link locked."}, status=400)

        otp = request.data.get("otp", "").strip()
        decision = request.data.get("decision", "").lower()

        if decision not in ("approve", "deny"):
            return Response({"detail": "decision must be 'approve' or 'deny'."}, status=400)

        # Verify OTP
        if hash_otp(otp) != link.otp_hash:
            DataRequestApprovalLink.objects.filter(pk=link.pk).update(
                otp_attempts=link.otp_attempts + 1
            )
            remaining = max(0, 3 - (link.otp_attempts + 1))
            return Response(
                {"detail": f"Incorrect OTP. {remaining} attempt(s) remaining."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP correct — apply decision
        new_status = RequestStatus.APPROVED if decision == "approve" else RequestStatus.DENIED
        DataRequest.objects.filter(pk=link.request_id).update(
            status=new_status,
            approved_by=link.request.vault.user,
            approved_at=timezone.now(),
        )
        DataRequestApprovalLink.objects.filter(pk=link.pk).update(used_at=timezone.now())

        return Response({"status": new_status, "decision": decision})

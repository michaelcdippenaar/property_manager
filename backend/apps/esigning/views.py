import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.leases.models import Lease
from apps.tenant_portal.views import get_tenant_leases

from . import services
from .models import ESigningPublicLink, ESigningSubmission
from .serializers import ESigningSubmissionSerializer

logger = logging.getLogger(__name__)


def accessible_leases_queryset(user):
    """
    Same lease visibility as LeaseViewSet.get_queryset — used for esigning scope
    and to ensure staff only create submissions for leases they may access.
    """
    qs = Lease.objects.all()
    if user.role == User.Role.TENANT:
        return qs.filter(pk__in=get_tenant_leases(user).values_list("pk", flat=True))
    if user.role == User.Role.ADMIN:
        return qs
    if user.role == User.Role.AGENT:
        return qs.filter(
            Q(unit__property__agent=user)
            | Q(unit__property__agent__isnull=True)
            | Q(unit__property__agent__role=User.Role.ADMIN)
        ).distinct()
    return qs.none()


def esigning_submissions_for_user(user):
    base = ESigningSubmission.objects.select_related("lease__unit__property")
    lease_ids = accessible_leases_queryset(user).values_list("pk", flat=True)
    return base.filter(lease_id__in=lease_ids)


def can_manage_esigning(user):
    return user.role in (User.Role.ADMIN, User.Role.AGENT)


class ScopedESigningQuerysetMixin:
    def get_queryset(self):
        qs = esigning_submissions_for_user(self.request.user)
        lease_id = self.request.query_params.get("lease_id")
        if lease_id:
            qs = qs.filter(lease_id=lease_id)
        return qs


class ESigningSubmissionListCreateView(ScopedESigningQuerysetMixin, ListCreateAPIView):
    serializer_class = ESigningSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not can_manage_esigning(request.user):
            return Response(
                {"detail": "Only staff may create signing submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lease_id = request.data.get("lease_id")
        signers = request.data.get("signers", [])
        signing_mode = request.data.get("signing_mode", "sequential")

        if not lease_id:
            return Response({"error": "lease_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not signers:
            return Response({"error": "At least one signer is required"}, status=status.HTTP_400_BAD_REQUEST)
        if signing_mode not in ("sequential", "parallel"):
            return Response(
                {"error": 'signing_mode must be "sequential" or "parallel"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lease = get_object_or_404(accessible_leases_queryset(request.user), pk=lease_id)

        try:
            result = services.create_lease_submission(lease, signers, signing_mode=signing_mode)
        except Exception as e:
            logger.exception("DocuSeal submission failed")
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        template_data = result["template"]
        submission_list = result["submission"]

        if isinstance(submission_list, list) and submission_list:
            first = submission_list[0]
            submission_id = first.get("submission_id") or first.get("id", "")
        else:
            submission_id = ""

        signer_records = []
        for idx, item in enumerate(submission_list if isinstance(submission_list, list) else [submission_list]):
            signer_records.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name", ""),
                    "email": item.get("email", ""),
                    "role": item.get("role", ""),
                    "status": item.get("status", "sent"),
                    "slug": item.get("slug", ""),
                    "embed_src": item.get("embed_src", ""),
                    "completed_at": item.get("completed_at"),
                    "order": item.get("order", idx if signing_mode == "sequential" else 0),
                }
            )

        signer_records.sort(key=lambda s: s.get("order", 0))

        obj = ESigningSubmission.objects.create(
            lease=lease,
            docuseal_submission_id=str(submission_id),
            docuseal_template_id=str(template_data.get("id", "")),
            status=ESigningSubmission.Status.PENDING,
            signing_mode=signing_mode,
            signers=signer_records,
            created_by=request.user,
        )

        return Response(ESigningSubmissionSerializer(obj).data, status=status.HTTP_201_CREATED)


class ESigningSubmissionDetailView(ScopedESigningQuerysetMixin, RetrieveAPIView):
    serializer_class = ESigningSubmissionSerializer
    permission_classes = [IsAuthenticated]


class ESigningSignerStatusView(APIView):
    """
    GET /api/v1/esigning/submissions/<pk>/signer-status/

    Returns the current signing workflow state:
    - current_signer: who needs to sign now
    - completed: list of signers who have signed
    - pending: list of signers waiting their turn
    - signing_mode: sequential or parallel
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(esigning_submissions_for_user(request.user), pk=pk)
        signers = obj.signers or []

        completed = []
        current = None
        pending = []
        declined = []

        for s in signers:
            st = (s.get("status") or "").lower()
            info = {
                "id": s.get("id"),
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "role": s.get("role", ""),
                "status": s.get("status", ""),
                "order": s.get("order", 0),
                "completed_at": s.get("completed_at"),
            }
            if st in ("completed", "signed"):
                completed.append(info)
            elif st == "declined":
                declined.append(info)
            elif current is None and obj.signing_mode == "sequential":
                current = info
            else:
                if obj.signing_mode == "parallel":
                    pending.append(info)
                else:
                    pending.append(info)

        return Response(
            {
                "submission_id": obj.pk,
                "status": obj.status,
                "signing_mode": obj.signing_mode,
                "signed_pdf_url": obj.signed_pdf_url or None,
                "current_signer": current,
                "completed_signers": completed,
                "pending_signers": pending,
                "declined_signers": declined,
                "progress": {
                    "total": len(signers),
                    "completed": len(completed),
                    "declined": len(declined),
                    "pending": len(pending) + (1 if current else 0),
                },
            }
        )


class ESigningResendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_esigning(request.user):
            return Response(
                {"detail": "Only staff may resend signing invitations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from django.conf import settings

        import requests as req

        obj = get_object_or_404(esigning_submissions_for_user(request.user), pk=pk)
        submitter_id = request.data.get("submitter_id")
        if not submitter_id:
            return Response({"error": "submitter_id required"}, status=status.HTTP_400_BAD_REQUEST)

        api_url = getattr(settings, "DOCUSEAL_API_URL", "https://api.docuseal.com")
        api_key = getattr(settings, "DOCUSEAL_API_KEY", "")
        try:
            r = req.post(
                f"{api_url.rstrip('/')}/api/submitters/{submitter_id}/send_email",
                headers={"X-Auth-Token": api_key, "Content-Type": "application/json"},
                timeout=15,
            )
            r.raise_for_status()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"ok": True})


class ESigningPublicSignDetailView(APIView):
    """
    Public (no auth): resolve UUID signing link → DocuSeal embed URL for one signer.
    Used by the admin SPA route /sign/:token without logging in.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, link_id):
        try:
            uid = uuid.UUID(str(link_id))
        except (ValueError, TypeError, AttributeError):
            return Response({"detail": "Invalid link."}, status=status.HTTP_404_NOT_FOUND)

        link = (
            ESigningPublicLink.objects.select_related("submission__lease__unit__property")
            .filter(pk=uid)
            .first()
        )
        if not link:
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_404_NOT_FOUND)
        if link.is_expired():
            return Response({"detail": "This signing link has expired."}, status=status.HTTP_410_GONE)

        sub = link.submission
        if sub.status in ("completed", "declined"):
            return Response(
                {"detail": "This signing request is no longer active."},
                status=status.HTTP_410_GONE,
            )

        signer = sub.get_signer_by_submitter_id(link.submitter_id)
        if not signer:
            return Response({"detail": "Invalid link."}, status=status.HTTP_404_NOT_FOUND)

        st = (signer.get("status") or "").lower()
        if st in ("completed", "signed", "declined"):
            return Response(
                {"detail": "You have already completed or declined this document."},
                status=status.HTTP_410_GONE,
            )

        embed = (signer.get("embed_src") or "").strip()
        if not embed:
            return Response(
                {"detail": "Signing is not available yet. Try again later."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease_label = f"{sub.lease.unit.property.name} — Unit {sub.lease.unit.unit_number}"
        return Response(
            {
                "embed_src": embed,
                "document_title": lease_label,
                "signer_name": signer.get("name") or "",
                "signer_email": signer.get("email") or "",
                "submission_status": sub.status,
                "signer_status": signer.get("status") or "",
            }
        )


class ESigningCreatePublicLinkView(APIView):
    """Staff: create a UUID link to share by SMS/email for passwordless signing."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not can_manage_esigning(request.user):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        submission = get_object_or_404(esigning_submissions_for_user(request.user), pk=pk)
        raw_sid = request.data.get("submitter_id")
        if raw_sid is None:
            return Response({"error": "submitter_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            submitter_id = int(raw_sid)
        except (TypeError, ValueError):
            return Response({"error": "submitter_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        signer = submission.get_signer_by_submitter_id(submitter_id)
        if not signer:
            return Response({"error": "Unknown submitter for this submission"}, status=status.HTTP_400_BAD_REQUEST)

        if submission.status in ("completed", "declined"):
            return Response({"error": "Submission is finished"}, status=status.HTTP_400_BAD_REQUEST)

        st = (signer.get("status") or "").lower()
        if st in ("completed", "signed", "declined"):
            return Response({"error": "This signer has already finished"}, status=status.HTTP_400_BAD_REQUEST)

        send_email_flag = bool(request.data.get("send_email"))
        if send_email_flag and not (signer.get("email") or "").strip():
            return Response(
                {"error": "Signer has no email address on file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        default_days = int(getattr(settings, "ESIGNING_PUBLIC_LINK_EXPIRY_DAYS", 14))
        raw_days = request.data.get("expires_in_days")
        try:
            days = int(raw_days) if raw_days is not None else default_days
        except (TypeError, ValueError):
            days = default_days
        days = max(1, min(days, 90))

        link = ESigningPublicLink.objects.create(
            submission=submission,
            submitter_id=submitter_id,
            expires_at=timezone.now() + timedelta(days=days),
        )

        path = f"/sign/{link.pk}/"
        base = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "") or ""
        signing_url = f"{base}{path}" if base else None
        origin = (request.data.get("public_app_origin") or "").strip().rstrip("/")
        if not signing_url and origin:
            signing_url = f"{origin}{path}"

        email_sent = False
        email_error = ""
        if send_email_flag:
            from apps.notifications.services import send_email as notify_send_email

            to_email = (signer.get("email") or "").strip()
            if not signing_url:
                link.delete()
                return Response(
                    {
                        "error": (
                            "Cannot build an absolute signing URL for email. Set "
                            "SIGNING_PUBLIC_APP_BASE_URL in settings, or pass "
                            "public_app_origin (your admin app origin, e.g. "
                            "https://admin.example.com)."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            prop = submission.lease.unit.property
            doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"
            name = (signer.get("name") or "").strip()
            salutation = f"Hello {name}," if name else "Hello,"
            exp = link.expires_at.strftime("%d %b %Y")
            subject = f"Please sign: {doc_title}"
            plain = (
                f"{salutation}\n\n"
                f"Please review and sign your document using this link:\n{signing_url}\n\n"
                f"This link expires on {exp}.\n\n"
                f"If you did not expect this email, you can ignore it.\n"
            )
            html = (
                f"<p>{salutation}</p>"
                f"<p>Please review and sign using the button or link below.</p>"
                f'<p><a href="{signing_url}" style="display:inline-block;padding:10px 16px;'
                f'background:#1e3a5f;color:#fff;text-decoration:none;border-radius:8px;">'
                f"Open signing page</a></p>"
                f"<p style=\"font-size:13px;color:#666;\"><a href=\"{signing_url}\">{signing_url}</a></p>"
                f"<p style=\"font-size:12px;color:#999;\">This link expires on {exp}.</p>"
            )
            email_sent = notify_send_email(subject, plain, to_email, html_body=html)
            if not email_sent:
                email_error = "Email could not be sent. Check server logs and NotificationLog."

        payload = {
            "uuid": str(link.pk),
            "expires_at": link.expires_at.isoformat(),
            "sign_path": path,
            "signing_url": signing_url,
            "email_sent": email_sent,
        }
        if email_error:
            payload["email_error"] = email_error
        return Response(payload, status=status.HTTP_201_CREATED)


class ESigningWebhookInfoView(APIView):
    """
    Staff: exact URL and verify mode for pasting into DocuSeal → Webhooks.
    DocuSeal initiates the connection (POST); Tremly does not call DocuSeal to “register” the hook.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_manage_esigning(request.user):
            return Response({"detail": "Only staff may view webhook settings."}, status=status.HTTP_403_FORBIDDEN)

        configured = getattr(settings, "ESIGNING_WEBHOOK_PUBLIC_URL", "").strip().rstrip("/")
        if configured:
            webhook_url = f"{configured}/api/v1/esigning/webhook/"
        else:
            webhook_url = request.build_absolute_uri(reverse("esigning-webhook"))

        secret = (getattr(settings, "DOCUSEAL_WEBHOOK_SECRET", "") or "").strip()
        header_name = (getattr(settings, "DOCUSEAL_WEBHOOK_HEADER_NAME", "") or "").strip()
        if not secret:
            verify_mode = "none"
        elif header_name:
            verify_mode = "static_header"
        else:
            verify_mode = "hmac_sha256_body"

        console = (getattr(settings, "DOCUSEAL_HOOK_URL", "") or "").strip() or None

        return Response({
            "webhook_url": webhook_url.rstrip("/") + "/",
            "verify_mode": verify_mode,
            "webhook_header_name": header_name or None,
            "docuseal_console_hooks_url": console,
        })

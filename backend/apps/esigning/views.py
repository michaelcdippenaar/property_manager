import logging
import uuid
from datetime import timedelta

import requests as http_requests
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

        # Auto-create public signing links and send Tremly emails.
        # DocuSeal never sends its own emails (send_email=False above).
        # For sequential: only email the first signer (order 0).
        # For parallel: email all signers at once.
        _auto_send_signing_links(obj, signers, request)

        return Response(ESigningSubmissionSerializer(obj).data, status=status.HTTP_201_CREATED)


def _auto_send_signing_links(submission, original_signers, request):
    """
    After creating a submission, create ESigningPublicLink for each signer
    and email them the Tremly /sign/<uuid>/ URL.
    For sequential mode, only the first signer gets emailed now;
    subsequent signers are emailed by the webhook handler when each completes.
    """
    from datetime import timedelta

    default_days = int(getattr(settings, "ESIGNING_PUBLIC_LINK_EXPIRY_DAYS", 14))
    base_url = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "").rstrip("/")
    if not base_url:
        # Fallback: try to build from request
        base_url = f"{request.scheme}://{request.get_host()}"

    prop = submission.lease.unit.property
    doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"

    for signer in submission.signers:
        submitter_id = signer.get("id")
        if not submitter_id:
            continue

        order = signer.get("order", 0)

        # Sequential: only send to the first signer now
        if submission.signing_mode == "sequential" and order > 0:
            continue

        email = (signer.get("email") or "").strip()
        name = (signer.get("name") or "").strip()
        if not email:
            continue

        # Check if the original signer data requested send_email
        orig = next(
            (s for s in original_signers if s.get("email", "").strip() == email),
            {},
        )
        if not orig.get("send_email", True):
            continue

        link = ESigningPublicLink.objects.create(
            submission=submission,
            submitter_id=int(submitter_id),
            expires_at=timezone.now() + timedelta(days=default_days),
        )

        signing_url = f"{base_url}/sign/{link.pk}/"
        exp = link.expires_at.strftime("%d %b %Y")
        salutation = f"Hello {name}," if name else "Hello,"

        subject = f"Please sign: {doc_title}"
        plain = (
            f"{salutation}\n\n"
            f"You have been invited to review and sign a lease agreement "
            f"for {doc_title}.\n\n"
            f"Please sign using this link:\n{signing_url}\n\n"
            f"This link expires on {exp}.\n\n"
            f"If you did not expect this email, you can safely ignore it.\n"
        )
        html = (
            f"<p>{salutation}</p>"
            f"<p>You have been invited to review and sign a lease agreement "
            f"for <strong>{doc_title}</strong>.</p>"
            f'<p><a href="{signing_url}" style="display:inline-block;padding:12px 24px;'
            f'background:#1e3a5f;color:#fff;text-decoration:none;border-radius:8px;'
            f'font-weight:600;">Review &amp; Sign</a></p>'
            f'<p style="font-size:13px;color:#666;">'
            f'Or open this link: <a href="{signing_url}">{signing_url}</a></p>'
            f'<p style="font-size:12px;color:#999;">This link expires on {exp}.</p>'
        )
        try:
            from apps.notifications.services import send_email
            send_email(subject, plain, email, html_body=html)
        except Exception:
            logger.exception(
                "Failed to send signing email to %s for submission %s",
                email, submission.pk,
            )


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

        obj = get_object_or_404(esigning_submissions_for_user(request.user), pk=pk)
        submitter_id = request.data.get("submitter_id")
        if not submitter_id:
            return Response({"error": "submitter_id required"}, status=status.HTTP_400_BAD_REQUEST)

        api_url = getattr(settings, "DOCUSEAL_API_URL", "https://api.docuseal.com")
        api_key = getattr(settings, "DOCUSEAL_API_KEY", "")
        try:
            r = http_requests.post(
                f"{api_url.rstrip('/')}/submitters/{submitter_id}/send_email",
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


# ── Headless signing endpoints (no iframe) ───────────────────────────────


class ESigningDocumentView(APIView):
    """
    Public (no auth): fetch the document PDF for a signing link.
    GET /api/v1/esigning/public-sign/<uuid>/document/

    Returns the PDF as a proxied binary response so the Vue app can
    render it with PDF.js without CORS issues.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, link_id):
        link, signer, sub, error_resp = _resolve_public_link(link_id)
        if error_resp:
            return error_resp

        try:
            pdf_url = services.get_document_pdf_url(int(signer["id"]))
        except Exception:
            logger.exception("Failed to get document URL from DocuSeal")
            pdf_url = None

        if not pdf_url:
            return Response(
                {"detail": "Document not available yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Proxy the PDF from DocuSeal so the frontend doesn't need CORS access
        try:
            r = http_requests.get(pdf_url, timeout=30, stream=True)
            r.raise_for_status()
        except Exception:
            return Response(
                {"detail": "Could not fetch document."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        from django.http import HttpResponse as DjHttpResponse
        resp = DjHttpResponse(r.content, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="document.pdf"'
        resp["Cache-Control"] = "private, max-age=300"
        return resp


class ESigningFieldsView(APIView):
    """
    Public (no auth): get the signing field positions for a public link.
    GET /api/v1/esigning/public-sign/<uuid>/fields/

    Returns the field definitions (name, type, position, page) that the
    signer needs to fill, filtered to their role only.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, link_id):
        link, signer, sub, error_resp = _resolve_public_link(link_id)
        if error_resp:
            return error_resp

        try:
            template_data = services.get_template_fields(int(sub.docuseal_template_id))
        except Exception:
            logger.exception("Failed to get template fields from DocuSeal")
            return Response(
                {"detail": "Could not load field definitions."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        signer_role = signer.get("role", "")
        all_fields = []
        for doc in template_data.get("documents", []):
            for field in doc.get("fields", []):
                if field.get("role") == signer_role:
                    all_fields.append({
                        "name": field["name"],
                        "type": field.get("type", "text"),
                        "required": field.get("required", True),
                        "areas": field.get("areas", []),
                    })

        return Response({
            "signer_name": signer.get("name", ""),
            "signer_email": signer.get("email", ""),
            "signer_role": signer_role,
            "document_title": f"{sub.lease.unit.property.name} — Unit {sub.lease.unit.unit_number}",
            "total_pages": sum(
                max((a.get("page", 1) for a in f.get("areas", [{"page": 1}])), default=1)
                for f in all_fields
            ) if all_fields else 1,
            "fields": all_fields,
        })


class ESigningSubmitSignatureView(APIView):
    """
    Public (no auth): submit a signature for a signer via their public link.
    POST /api/v1/esigning/public-sign/<uuid>/submit/

    Request body:
    {
        "fields": [
            {"name": "Signature (First Party)", "value": "data:image/png;base64,..."},
            {"name": "Date (First Party)", "value": "2026-03-26"}
        ]
    }
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, link_id):
        link, signer, sub, error_resp = _resolve_public_link(link_id)
        if error_resp:
            return error_resp

        fields_input = request.data.get("fields", [])
        signature_svg = request.data.get("signature_svg", "")
        if not fields_input:
            return Response(
                {"error": "At least one field is required (signature)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Map to DocuSeal format
        docuseal_fields = []
        for f in fields_input:
            name = f.get("name", "").strip()
            value = f.get("value", "")
            if not name:
                continue
            docuseal_fields.append({
                "name": name,
                "default_value": value,
            })

        if not docuseal_fields:
            return Response(
                {"error": "No valid fields provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store vector signature on the signer record for future re-rendering
        if signature_svg and isinstance(signature_svg, str):
            signer["signature_svg"] = signature_svg
            sub.save(update_fields=["signers", "updated_at"])

        try:
            result = services.submit_signature(int(signer["id"]), docuseal_fields)
        except Exception as e:
            logger.exception("Failed to submit signature to DocuSeal")
            # Surface meaningful errors from DocuSeal (e.g. "already completed")
            detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    body = e.response.json()
                    detail = body.get('error', detail)
                except Exception:
                    pass
            if 'already completed' in detail.lower():
                return Response(
                    {"error": "This document has already been signed."},
                    status=status.HTTP_410_GONE,
                )
            return Response(
                {"error": "Signing service error. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "ok": True,
            "submitter_status": result.get("status", "completed"),
            "message": "Your signature has been submitted successfully.",
        })


def _resolve_public_link(link_id):
    """
    Shared helper: validate a public signing link UUID and return
    (link, signer, submission, None) on success or
    (None, None, None, Response) on error.
    """
    try:
        uid = uuid.UUID(str(link_id))
    except (ValueError, TypeError, AttributeError):
        return None, None, None, Response(
            {"detail": "Invalid link."}, status=status.HTTP_404_NOT_FOUND
        )

    link = (
        ESigningPublicLink.objects.select_related("submission__lease__unit__property")
        .filter(pk=uid)
        .first()
    )
    if not link:
        return None, None, None, Response(
            {"detail": "Invalid or expired link."}, status=status.HTTP_404_NOT_FOUND
        )
    if link.is_expired():
        return None, None, None, Response(
            {"detail": "This signing link has expired."}, status=status.HTTP_410_GONE
        )

    sub = link.submission
    if sub.status in ("completed", "declined"):
        return None, None, None, Response(
            {"detail": "This signing request is no longer active."},
            status=status.HTTP_410_GONE,
        )

    signer = sub.get_signer_by_submitter_id(link.submitter_id)
    if not signer:
        return None, None, None, Response(
            {"detail": "Invalid link."}, status=status.HTTP_404_NOT_FOUND
        )

    st = (signer.get("status") or "").lower()
    if st in ("completed", "signed", "declined"):
        return None, None, None, Response(
            {"detail": "You have already completed or declined this document."},
            status=status.HTTP_410_GONE,
        )

    return link, signer, sub, None

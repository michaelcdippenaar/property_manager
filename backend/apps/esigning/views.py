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

from apps.accounts.permissions import IsAgentOrAdmin
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.leases.models import Lease
from apps.tenant_portal.views import get_tenant_leases

from . import services
from .audit import log_esigning_event
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
        from apps.properties.access import get_accessible_property_ids
        prop_ids = get_accessible_property_ids(user)
        return qs.filter(unit__property_id__in=prop_ids)
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

        # Use native signing by default
        try:
            obj = services.create_native_submission(lease, signers, signing_mode=signing_mode)
            obj.created_by = request.user
            obj.save(update_fields=['created_by'])
        except Exception as e:
            logger.exception("Native submission creation failed")
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

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
            submitter_id=int(submitter_id) if submitter_id else None,
            signer_role=signer.get("role", ""),
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

    def delete(self, request, pk):
        if not can_manage_esigning(request.user):
            return Response(
                {"detail": "Only staff may cancel signing submissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = get_object_or_404(esigning_submissions_for_user(request.user), pk=pk)
        if obj.status == ESigningSubmission.Status.COMPLETED:
            return Response(
                {"detail": "Cannot cancel a completed submission."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Block if any signer has already signed — they must be notified and a
        # valid reason recorded before cancellation is permitted.
        signed_signers = [
            s for s in (obj.signers or [])
            if (s.get('status') or '').lower() in ('completed', 'signed')
        ]
        if signed_signers:
            names = ', '.join(s.get('name', 'Unknown') for s in signed_signers)
            return Response(
                {"detail": f"Cannot cancel: {names} has already signed. "
                           "Notify all parties and obtain consent before withdrawing a partially-signed document."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ESigningSignerStatusView(APIView):
    """
    GET /api/v1/esigning/submissions/<pk>/signer-status/

    Returns the current signing workflow state:
    - current_signer: who needs to sign now
    - completed: list of signers who have signed
    - pending: list of signers waiting their turn
    - signing_mode: sequential or parallel
    """

    permission_classes = [IsAgentOrAdmin]

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
                "signed_pdf_url": request.build_absolute_uri(obj.signed_pdf_url) if obj.signed_pdf_url else None,
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


class ESigningDownloadSignedView(APIView):
    """
    GET /api/v1/esigning/submissions/<pk>/download/
    Fetches a fresh signed PDF URL from DocuSeal and redirects to it.
    DocuSeal file URLs contain time-limited tokens, so we always fetch
    a fresh one to avoid 500 errors from expired links.
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request, pk):
        qs = ESigningSubmission.objects.filter(
            lease__in=accessible_leases_queryset(request.user)
        )
        obj = get_object_or_404(qs, pk=pk)

        if obj.status != ESigningSubmission.Status.COMPLETED:
            return Response(
                {"detail": "Document has not been fully signed yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Native signing: serve local PDF
        if obj.signing_backend == ESigningSubmission.SigningBackend.NATIVE:
            if obj.signed_pdf_file:
                return Response({"url": request.build_absolute_uri(obj.signed_pdf_file.url)})
            return Response(
                {"detail": "Signed document not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # DocuSeal: fetch fresh URL from API
        pdf_url = None
        docuseal_id = obj.docuseal_submission_id
        if docuseal_id:
            try:
                sub_data = services._docuseal_get(f'/submissions/{docuseal_id}')
                docs = sub_data.get('documents') or []
                if docs:
                    pdf_url = docs[0].get('url', '')
            except Exception:
                logger.exception("Failed to fetch fresh signed URL from DocuSeal")

        if not pdf_url:
            pdf_url = obj.signed_pdf_url

        if not pdf_url:
            return Response(
                {"detail": "Signed document not available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Ensure relative URLs get a full hostname
        if pdf_url.startswith('/'):
            pdf_url = request.build_absolute_uri(pdf_url)

        return Response({"url": pdf_url})


class ESigningTestPdfView(APIView):
    """
    GET /api/v1/esigning/submissions/<pk>/test-pdf/
    Regenerates the signed PDF on the fly (no caching) and returns it directly.
    No auth required — dev/testing only.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        from django.http import HttpResponse
        sub = get_object_or_404(ESigningSubmission, pk=pk)
        pdf_bytes = services.generate_signed_pdf(sub)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="test_lease_{pk}.pdf"'
        return response


class GotenbergHealthView(APIView):
    """
    GET /api/v1/esigning/gotenberg/health/
    Returns the Gotenberg service health status (Chromium + LibreOffice engines).
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        if not can_manage_esigning(request.user):
            return Response(
                {"detail": "Only staff may check service health."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            from .gotenberg import health_check
            data = health_check()
            return Response(data)
        except Exception as e:
            return Response(
                {"status": "down", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class ESigningResendView(APIView):
    permission_classes = [IsAgentOrAdmin]

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

    def _resolve_link(self, link_id):
        """Common link validation for public signing endpoints."""
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

        # Find signer: by role for native, by submitter_id for docuseal
        signer = None
        if sub.signing_backend == ESigningSubmission.SigningBackend.NATIVE:
            role = link.signer_role
            for s in sub.signers:
                if s.get("role", "").lower() == role.lower():
                    signer = s
                    break
        else:
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

        return link, sub, signer, None

    def get(self, request, link_id):
        link, sub, signer, error = self._resolve_link(link_id)
        if error:
            return error

        lease_label = f"{sub.lease.unit.property.name} — Unit {sub.lease.unit.unit_number}"

        log_esigning_event(
            sub, "document_viewed", request=request,
            signer_role=signer.get("role", ""),
        )

        if sub.signing_backend == ESigningSubmission.SigningBackend.NATIVE:
            return Response({
                "signing_backend": "native",
                "document_title": lease_label,
                "signer_name": signer.get("name") or "",
                "signer_email": signer.get("email") or "",
                "signer_role": signer.get("role") or "",
                "submission_status": sub.status,
                "signer_status": signer.get("status") or "",
            })

        # DocuSeal flow
        embed = (signer.get("embed_src") or "").strip()
        if not embed:
            return Response(
                {"detail": "Signing is not available yet. Try again later."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "signing_backend": "docuseal",
            "embed_src": embed,
            "document_title": lease_label,
            "signer_name": signer.get("name") or "",
            "signer_email": signer.get("email") or "",
            "signer_role": signer.get("role") or "",
            "submission_status": sub.status,
            "signer_status": signer.get("status") or "",
        })


class ESigningPublicDocumentView(APIView):
    """
    Public (no auth): GET the filled lease HTML + signing field info for native signing.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, link_id):
        link, sub, signer, error = ESigningPublicSignDetailView()._resolve_link(link_id)
        if error:
            return error

        if sub.signing_backend != ESigningSubmission.SigningBackend.NATIVE:
            return Response(
                {"detail": "This endpoint is only for native signing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signer_role = signer.get("role", "")

        # Apply previously captured data so next signer sees filled values
        display_html = services.apply_captured_data(
            sub.document_html, sub.captured_data or {}
        )

        fields = services.extract_signer_fields(display_html, signer_role)
        already_signed = services.get_already_signed_fields(sub)
        editable_merge_fields = services.extract_editable_merge_fields(
            display_html, signer_role
        )

        return Response({
            "html": display_html,
            "signer_role": signer_role,
            "fields": fields,
            "editable_merge_fields": editable_merge_fields,
            "already_captured": sub.captured_data or {},
            "already_signed": already_signed,
            "signing_mode": sub.signing_mode,
        })


class ESigningPublicSubmitSignatureView(APIView):
    """
    Public (no auth): POST signature data to complete native signing for one signer.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, link_id):
        link, sub, signer, error = ESigningPublicSignDetailView()._resolve_link(link_id)
        if error:
            return error

        if sub.signing_backend != ESigningSubmission.SigningBackend.NATIVE:
            return Response(
                {"detail": "This endpoint is only for native signing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signed_fields = request.data.get("fields", [])
        captured_fields = request.data.get("captured_fields", {})
        consent = request.data.get("consent", {})

        if not signed_fields:
            return Response(
                {"error": "No signed fields provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not consent.get("agreed"):
            return Response(
                {"error": "Consent must be given to sign electronically."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Collect audit data from request
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
        audit_data = {
            "ip_address": ip,
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "consent_given_at": consent.get("timestamp", timezone.now().isoformat()),
        }

        signer_role = signer.get("role", "")

        log_esigning_event(
            sub, "consent_given", request=request,
            signer_role=signer_role,
            metadata={"consent_timestamp": consent.get("timestamp", "")},
        )

        try:
            from django.db import transaction
            with transaction.atomic():
                sub, all_completed = services.complete_native_signer(
                    sub, signer_role, signed_fields, audit_data,
                    captured_fields=captured_fields or None,
                )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        log_esigning_event(
            sub, "signing_completed", request=request,
            signer_role=signer_role,
            metadata={"fields_signed": [f["fieldName"] for f in signed_fields]},
        )

        if all_completed:
            log_esigning_event(
                sub, "document_completed", request=request,
                signer_role=signer_role,
                metadata={"total_signers": len(sub.signers)},
            )

        # Sync captured merge field data back to Person/Occupant models
        if captured_fields:
            try:
                services.sync_captured_data_to_models(sub)
            except Exception:
                logger.exception("Failed to sync captured data for submission %s", sub.pk)

        # Post-signing actions
        from .webhooks import _broadcast_ws, _activate_lease, _get_next_signer, _notify_next_signer, _notify_staff, _email_signed_copy_to_signers

        if all_completed:
            _activate_lease(sub)
            # Generate signed PDF
            try:
                import hashlib as _hashlib
                from django.core.files.base import ContentFile
                pdf_bytes = services.generate_signed_pdf(sub)
                filename = f"signed_lease_{sub.pk}.pdf"
                sub.signed_pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
                sub.signed_pdf_url = sub.signed_pdf_file.url
                sub.signed_pdf_hash = _hashlib.sha256(pdf_bytes).hexdigest()
                sub.save(update_fields=["signed_pdf_file", "signed_pdf_url", "signed_pdf_hash", "updated_at"])
            except Exception:
                logger.exception("Failed to generate signed PDF for submission %s", sub.pk)

            _broadcast_ws(sub.pk, {
                "type": "submission_completed",
                "submission_id": sub.pk,
                "signed_pdf_url": sub.signed_pdf_url,
                "signers": sub.signers,
            })
            _notify_staff(sub, "submission.completed", {})
            _email_signed_copy_to_signers(sub, {})
        else:
            # Notify next signer if sequential
            if sub.signing_mode == ESigningSubmission.SigningMode.SEQUENTIAL:
                next_signer = _get_next_signer(sub.signers)
                if next_signer:
                    _notify_next_signer(sub, next_signer)

            _broadcast_ws(sub.pk, {
                "type": "signer_completed",
                "submission_id": sub.pk,
                "signers": sub.signers,
            })
            _notify_staff(sub, "form.completed", {"submitter": signer})

        return Response({
            "status": "completed",
            "submission_status": sub.status,
            "all_completed": all_completed,
        })


class ESigningCreatePublicLinkView(APIView):
    """Staff: create a UUID link to share by SMS/email for passwordless signing."""

    permission_classes = [IsAgentOrAdmin]

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
            signer_role=signer.get("role", ""),
            expires_at=timezone.now() + timedelta(days=days),
        )

        path = f"/sign/{link.pk}/"
        base = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "") or ""
        signing_url = f"{base}{path}" if base else None
        origin = (request.data.get("public_app_origin") or "").strip().rstrip("/")
        if not signing_url and origin:
            signing_url = f"{origin}{path}"

        log_esigning_event(
            submission, "link_created", request=request,
            signer_role=signer.get("role", ""),
            user=request.user,
            metadata={"link_id": str(link.pk), "submitter_id": submitter_id},
        )

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
    Staff: exact URL and verify mode for pasting into DocuSeal Webhooks.
    DocuSeal initiates the connection (POST); Tremly does not call DocuSeal to register the hook.
    """

    permission_classes = [IsAgentOrAdmin]

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



class ESigningPublicCompletedView(APIView):
    """
    Public (no auth): fire-and-forget callback from the embedded DocuSeal form's
    @completed event. This is a belt-and-suspenders fallback alongside the
    DocuSeal webhook — if the webhook is delayed or missed, this endpoint
    triggers the same signer-status refresh from DocuSeal's API.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, link_id):
        try:
            uid = uuid.UUID(str(link_id))
        except (ValueError, TypeError, AttributeError):
            return Response({"ok": True})  # Silently accept — it's fire-and-forget

        link = (
            ESigningPublicLink.objects
            .select_related("submission")
            .filter(pk=uid)
            .first()
        )
        if not link:
            return Response({"ok": True})

        sub = link.submission
        signer = sub.get_signer_by_submitter_id(link.submitter_id)
        if not signer:
            return Response({"ok": True})

        # Only act if signer hasn't been marked completed yet (webhook may have beaten us)
        st = (signer.get("status") or "").lower()
        if st in ("completed", "signed"):
            return Response({"ok": True})

        # Fetch fresh status from DocuSeal
        try:
            submitter_data = services.get_submitter(int(signer["id"]))
            ds_status = (submitter_data.get("status") or "").lower()
            if ds_status == "completed":
                signer["status"] = "completed"
                signer["completed_at"] = submitter_data.get("completed_at")
                sub.save(update_fields=["signers", "updated_at"])
                logger.info(
                    "Completion callback updated signer %s on submission %s",
                    signer["id"], sub.pk,
                )
        except Exception:
            logger.debug("Completion callback: could not fetch submitter %s", signer.get("id"))

        return Response({"ok": True})


# NOTE: The old headless signing endpoints (ESigningDocumentView, ESigningFieldsView,
# ESigningSubmitSignatureView) were removed — the signing UI now uses DocuSeal's
# embedded form component (@docuseal/vue) which communicates directly with DocuSeal.

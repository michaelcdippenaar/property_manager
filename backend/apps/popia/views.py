"""
apps/popia/views.py

POPIA s23 / s24 API endpoints.

Tenant / Data Subject endpoints:
  POST /api/v1/popia/data-export/          — request a SAR export (creates ExportJob)
  POST /api/v1/popia/erasure-request/      — request account erasure (RTBF)
  GET  /api/v1/popia/my-requests/          — list own DSAR requests
  GET  /api/v1/popia/download/<token>/     — download signed export archive

Operator endpoints (admin / agency_admin):
  GET  /api/v1/popia/dsar-queue/           — list all DSAR requests (paginated, filterable)
  POST /api/v1/popia/dsar-queue/<id>/review/  — approve or deny a request
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAdminOrAgencyAdmin
from apps.audit.models import AuditEvent

from .models import DSARRequest, ExportJob
from .serializers import (
    DSARRequestCreateSerializer,
    DSARRequestSerializer,
    ExportJobSerializer,
    OperatorReviewSerializer,
)
from .services.export_service import run_export_job_async

logger = logging.getLogger(__name__)


def _log_audit(action: str, actor, target_repr: str, after_snapshot: dict, request=None):
    """Helper to write an AuditEvent for POPIA actions."""
    try:
        ip = None
        ua = ""
        if request:
            ip = request.META.get("REMOTE_ADDR")
            ua = request.META.get("HTTP_USER_AGENT", "")
        AuditEvent.objects.create(
            actor=actor,
            actor_email=actor.email if actor else "",
            action=action,
            target_repr=target_repr,
            after_snapshot=after_snapshot,
            ip_address=ip,
            user_agent=ua,
            retention_years=7,
        )
    except Exception as exc:
        logger.warning("popia audit log failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Tenant / Data-Subject views
# ─────────────────────────────────────────────────────────────────────────────

class DataExportRequestView(APIView):
    """
    POST /api/v1/popia/data-export/

    Create a Subject Access Request (SAR).  The export does NOT run automatically
    at submission — an operator must approve it via the DSAR queue first.

    This aligns SAR with the RTBF flow: operator oversight is a POPIA feature,
    not a bug (s23 allows up to 30 days; POPIA s23 requires operator review
    before disclosing personal information to ensure identity verification).

    Rate-limited: one pending/running export per user at a time.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Prevent duplicate pending jobs
        existing = DSARRequest.objects.filter(
            requester=request.user,
            request_type=DSARRequest.RequestType.SAR,
            status__in=[
                DSARRequest.Status.PENDING,
                DSARRequest.Status.IN_REVIEW,
                DSARRequest.Status.APPROVED,
            ],
        ).first()
        if existing:
            return Response(
                {
                    "detail": "You already have a pending data export request.",
                    "dsar_request": DSARRequestSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        input_data = {
            "request_type": "sar",
            "reason": request.data.get("reason", ""),
        }
        ser = DSARRequestCreateSerializer(data=input_data)
        ser.is_valid(raise_exception=True)

        dsar = DSARRequest.objects.create(
            requester=request.user,
            requester_email=request.user.email,
            agency_id=getattr(request.user, "agency_id", None),
            request_type=DSARRequest.RequestType.SAR,
            reason=ser.validated_data.get("reason", ""),
            status=DSARRequest.Status.PENDING,
        )

        # Write audit event
        _log_audit(
            "popia.sar_requested",
            request.user,
            f"DSARRequest #{dsar.pk}",
            {"request_type": "sar", "dsar_id": dsar.pk},
            request,
        )

        # Notify operators (same as RTBF)
        _notify_operators_sar(dsar)

        return Response(
            {
                "dsar_request": DSARRequestSerializer(dsar).data,
                "message": (
                    "Your data access request has been received and will be reviewed within 30 days. "
                    "You will receive an email with a download link once the operator has approved it."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ErasureRequestView(APIView):
    """
    POST /api/v1/popia/erasure-request/

    Create a Right-to-Be-Forgotten (RTBF) request.
    The request enters a 30-day review window — deletion is NOT automatic.
    An operator must approve it via the DSAR queue.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Prevent duplicate pending erasure requests
        existing = DSARRequest.objects.filter(
            requester=request.user,
            request_type=DSARRequest.RequestType.RTBF,
            status__in=[
                DSARRequest.Status.PENDING,
                DSARRequest.Status.IN_REVIEW,
                DSARRequest.Status.APPROVED,
            ],
        ).first()
        if existing:
            return Response(
                {
                    "detail": "You already have a pending erasure request.",
                    "dsar_request": DSARRequestSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        input_data = {
            "request_type": "rtbf",
            "reason": request.data.get("reason", ""),
        }
        ser = DSARRequestCreateSerializer(data=input_data)
        ser.is_valid(raise_exception=True)

        dsar = DSARRequest.objects.create(
            requester=request.user,
            requester_email=request.user.email,
            agency_id=getattr(request.user, "agency_id", None),
            request_type=DSARRequest.RequestType.RTBF,
            reason=ser.validated_data.get("reason", ""),
            status=DSARRequest.Status.PENDING,
        )

        _log_audit(
            "popia.rtbf_requested",
            request.user,
            f"DSARRequest #{dsar.pk}",
            {"request_type": "rtbf", "dsar_id": dsar.pk},
            request,
        )

        # Notify operators
        _notify_operators_rtbf(dsar)

        return Response(
            {
                "dsar_request": DSARRequestSerializer(dsar).data,
                "message": (
                    "Your erasure request has been received and will be reviewed within 30 days. "
                    "You will be notified of the outcome by email. "
                    "Note: some records may be retained for legal compliance purposes "
                    "(FICA 5-year, lease records 5-year, tax records 7-year)."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class MyDSARRequestsView(APIView):
    """GET /api/v1/popia/my-requests/ — list the current user's DSAR requests."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = DSARRequest.objects.filter(requester=request.user).order_by("-created_at")
        return Response(DSARRequestSerializer(qs, many=True).data)


class ExportDownloadView(APIView):
    """
    GET /api/v1/popia/download/<token>/

    Serve the export ZIP using the signed download token.

    POPIA binding: the data subject must be authenticated AS the account owner.
    The token alone is not sufficient — the requesting user must match the
    ExportJob's DSARRequest.requester.  This prevents URL-sharing leaking
    another person's personal data (POPIA s19 — reasonable security measures).

    Single-use enforcement: once served the job is marked CONSUMED and the
    same token cannot be used again (returns 410 Gone on reuse).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, token: str):
        try:
            job = ExportJob.objects.select_related("dsar_request__requester").get(
                download_token=token,
            )
        except ExportJob.DoesNotExist:
            raise Http404("Download link not found.")

        # ── Blocker 2: single-use — already consumed ──────────────────────────
        if job.status == ExportJob.JobStatus.CONSUMED:
            from rest_framework.response import Response as DRFResponse
            return DRFResponse(
                {"detail": "This download link has already been used and is no longer valid."},
                status=410,
            )

        if job.status != ExportJob.JobStatus.COMPLETED:
            raise Http404("Download link not found or export not ready.")

        # ── Blocker 1: bind token to the authenticated data subject ───────────
        requester = job.dsar_request.requester
        if requester is None or requester.pk != request.user.pk:
            from rest_framework.response import Response as DRFResponse
            return DRFResponse(
                {"detail": "You are not authorised to download this export."},
                status=403,
            )

        if job.is_expired:
            raise Http404("Download link has expired.")

        zip_path = Path(settings.MEDIA_ROOT) / job.archive_path
        if not zip_path.exists():
            raise Http404("Export file not found.")

        # ── Mark consumed BEFORE streaming so a failed stream can't be retried
        job.status = ExportJob.JobStatus.CONSUMED
        job.save(update_fields=["status", "updated_at"])

        _log_audit(
            "popia.export_downloaded",
            request.user,
            f"ExportJob #{job.pk}",
            {"job_id": job.pk, "dsar_id": job.dsar_request.pk},
            request,
        )

        # Use zip_path directly — Django FileResponse handles fd lifecycle
        response = FileResponse(
            zip_path.open("rb"),
            content_type="application/zip",
            as_attachment=True,
            filename=f"klikk_data_export_{job.dsar_request.requester_email}.zip",
        )
        return response


# ─────────────────────────────────────────────────────────────────────────────
# Operator views
# ─────────────────────────────────────────────────────────────────────────────

class DSARQueueView(APIView):
    """
    GET /api/v1/popia/dsar-queue/

    List all DSAR requests for the DSAR operator queue.
    Filterable by ?status= and ?request_type=
    Ordered by SLA deadline ascending (most urgent first).
    """
    permission_classes = [IsAuthenticated, IsAdminOrAgencyAdmin]

    def get(self, request):
        qs = DSARRequest.objects.select_related(
            "requester", "reviewed_by"
        ).order_by("sla_deadline")

        # Phase 2.6 — agency reviewers must never see another agency's DSAR
        # queue. ADMIN / superuser bypass for cross-tenant operator support.
        user = request.user
        is_admin = bool(getattr(user, "is_superuser", False) or getattr(user, "role", None) == User.Role.ADMIN)
        if not is_admin:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None:
                qs = qs.none()
            else:
                qs = qs.filter(agency_id=agency_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        type_filter = request.query_params.get("request_type")
        if type_filter:
            qs = qs.filter(request_type=type_filter)

        return Response(DSARRequestSerializer(qs, many=True).data)


def _build_retention_flags(user) -> dict:
    """
    Return a dict of retention flags for the given user.

    Checks:
      - has_active_lease: a Person linked to this user is the primary_tenant on any
        ACTIVE lease.
      - has_outstanding_payments: any of those leases have invoices in UNPAID or
        PARTIALLY_PAID status.

    These flags are informational only — they do NOT block erasure.  They surface
    RHA / FICA risk to the operator so they can make an informed decision.
    """
    from apps.leases.models import Lease
    from apps.payments.models import RentInvoice

    # Resolve to Person via the reverse OneToOne (Person.linked_user → related_name="person_profile")
    try:
        person = user.person_profile
    except Exception:
        person = None

    if person is None:
        return {"has_active_lease": False, "has_outstanding_payments": False}

    has_active_lease = Lease.objects.filter(
        primary_tenant=person,
        status=Lease.Status.ACTIVE,
    ).exists()

    has_outstanding_payments = RentInvoice.objects.filter(
        lease__primary_tenant=person,
        status__in=[
            RentInvoice.Status.UNPAID,
            RentInvoice.Status.PARTIALLY_PAID,
        ],
    ).exists()

    return {
        "has_active_lease": has_active_lease,
        "has_outstanding_payments": has_outstanding_payments,
    }


class DSARReviewView(APIView):
    """
    GET  /api/v1/popia/dsar-queue/<id>/review/  — fetch request detail + retention_flags
    POST /api/v1/popia/dsar-queue/<id>/review/  — approve or deny

    GET returns the DSAR request serialised data plus a `retention_flags` object:
      { "has_active_lease": bool, "has_outstanding_payments": bool }
    Flags are only computed for RTBF requests (meaningless for SAR).

    POST Approve or deny a DSAR request.

    For SAR approvals: creates the ExportJob and queues the export in the
        background.  The data subject receives an email when the ZIP is ready.
        Export only runs after operator approval — the operator has verified the
        requester's identity (POPIA s23 identity verification obligation).

    For RTBF approvals: immediately executes the erasure.

    For denials: marks denied and notifies the data subject.
    """
    permission_classes = [IsAuthenticated, IsAdminOrAgencyAdmin]

    def get(self, request, pk: int):
        try:
            dsar = DSARRequest.objects.select_related("requester").get(pk=pk)
        except DSARRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Phase 2.6 — block cross-agency review access. ADMIN bypass.
        user = request.user
        is_admin = bool(getattr(user, "is_superuser", False) or getattr(user, "role", None) == User.Role.ADMIN)
        if not is_admin:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None or dsar.agency_id != agency_id:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        retention_flags = None
        retention_flags_computed = False
        if dsar.request_type == DSARRequest.RequestType.RTBF and dsar.requester:
            retention_flags = _build_retention_flags(dsar.requester)
            retention_flags_computed = True

        _log_audit(
            "popia.dsar_review_opened",
            request.user,
            f"DSARRequest #{dsar.pk}",
            {
                "dsar_id": dsar.pk,
                "request_type": dsar.request_type,
                "retention_flags_computed": retention_flags_computed,
            },
            request,
        )

        return Response({
            "dsar_request": DSARRequestSerializer(dsar).data,
            "retention_flags": retention_flags,
        })

    def post(self, request, pk: int):
        try:
            dsar = DSARRequest.objects.select_related("requester").get(pk=pk)
        except DSARRequest.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Phase 2.6 — block cross-agency review access. ADMIN bypass.
        user = request.user
        is_admin = bool(getattr(user, "is_superuser", False) or getattr(user, "role", None) == User.Role.ADMIN)
        if not is_admin:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None or dsar.agency_id != agency_id:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if dsar.status not in (DSARRequest.Status.PENDING, DSARRequest.Status.IN_REVIEW):
            return Response(
                {"detail": f"Request is already {dsar.status} and cannot be reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = OperatorReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]

        dsar.reviewed_by = request.user
        dsar.reviewed_at = timezone.now()
        dsar.operator_notes = ser.validated_data.get("operator_notes", "")

        if action == "approve":
            # Compute retention flags before erasure (requester may be anonymised after)
            retention_flags = None
            if dsar.request_type == DSARRequest.RequestType.RTBF and dsar.requester:
                retention_flags = _build_retention_flags(dsar.requester)

            dsar.status = DSARRequest.Status.APPROVED
            dsar.save(update_fields=["status", "reviewed_by", "reviewed_at", "operator_notes", "updated_at"])

            _log_audit(
                "popia.dsar_approved",
                request.user,
                f"DSARRequest #{dsar.pk}",
                {
                    "dsar_id": dsar.pk,
                    "request_type": dsar.request_type,
                    "requester_email": dsar.requester_email,
                },
                request,
            )

            if dsar.request_type == DSARRequest.RequestType.RTBF:
                # For RTBF: execute the erasure immediately
                from .services.deletion_service import execute_erasure
                execute_erasure(dsar, reviewer=request.user)
            elif dsar.request_type == DSARRequest.RequestType.SAR:
                # For SAR: NOW queue the export (operator has verified identity)
                job, _created = ExportJob.objects.get_or_create(
                    dsar_request=dsar,
                    defaults={"agency_id": dsar.agency_id},
                )
                if job.status in (ExportJob.JobStatus.QUEUED, ExportJob.JobStatus.FAILED):
                    run_export_job_async(job.pk)

            return Response(
                {
                    "detail": "Request approved.",
                    "dsar_request": DSARRequestSerializer(dsar).data,
                    "retention_flags": retention_flags,
                }
            )

        else:  # deny
            dsar.status = DSARRequest.Status.DENIED
            dsar.denial_reason = ser.validated_data.get("denial_reason", "")
            dsar.save(update_fields=[
                "status", "reviewed_by", "reviewed_at",
                "operator_notes", "denial_reason", "updated_at",
            ])

            _log_audit(
                "popia.dsar_denied",
                request.user,
                f"DSARRequest #{dsar.pk}",
                {
                    "dsar_id": dsar.pk,
                    "request_type": dsar.request_type,
                    "requester_email": dsar.requester_email,
                    "denial_reason": dsar.denial_reason,
                },
                request,
            )

            _notify_data_subject_denial(dsar)

            return Response(
                {
                    "detail": "Request denied.",
                    "dsar_request": DSARRequestSerializer(dsar).data,
                }
            )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _notify_operators_sar(dsar: DSARRequest) -> None:
    """Send an internal alert email to privacy@klikk.co.za when a SAR is submitted."""
    try:
        from apps.notifications.services.email import send_template_email

        admin_email = getattr(settings, "POPIA_OFFICER_EMAIL", "privacy@klikk.co.za")
        base_url = getattr(settings, "ADMIN_FRONTEND_URL", "https://app.klikk.co.za")
        queue_url = f"{base_url}/admin/compliance/dsar-queue"

        send_template_email(
            template_id="popia_sar_alert",
            to_emails=admin_email,
            context={
                "recipient_name": "Information Officer",
                "requester_email": dsar.requester_email,
                "dsar_id": dsar.pk,
                "sla_deadline": dsar.sla_deadline.strftime("%d %B %Y"),
                "queue_url": queue_url,
                "cta_url": queue_url,
            },
        )
    except Exception as exc:
        logger.warning("popia: could not send SAR operator alert: %s", exc)


def _notify_operators_rtbf(dsar: DSARRequest) -> None:
    """Send an internal alert email to privacy@klikk.co.za when an RTBF is submitted."""
    try:
        from apps.notifications.services.email import send_template_email

        admin_email = getattr(settings, "POPIA_OFFICER_EMAIL", "privacy@klikk.co.za")
        base_url = getattr(settings, "ADMIN_FRONTEND_URL", "https://app.klikk.co.za")
        queue_url = f"{base_url}/admin/compliance/dsar-queue"

        send_template_email(
            template_id="popia_rtbf_alert",
            to_emails=admin_email,
            context={
                "recipient_name": "Information Officer",
                "requester_email": dsar.requester_email,
                "dsar_id": dsar.pk,
                "sla_deadline": dsar.sla_deadline.strftime("%d %B %Y"),
                "queue_url": queue_url,
                "cta_url": queue_url,
            },
        )
    except Exception as exc:
        logger.warning("popia: could not send RTBF operator alert: %s", exc)


def _notify_data_subject_denial(dsar: DSARRequest) -> None:
    """Email the data subject when their DSAR request is denied."""
    try:
        from apps.notifications.services.email import send_template_email

        send_template_email(
            template_id="popia_request_denied",
            to_emails=dsar.requester_email,
            context={
                "recipient_name": "Data Subject",
                "denial_reason": dsar.denial_reason,
                "request_type_display": dsar.get_request_type_display(),
                "cta_url": getattr(settings, "FRONTEND_BASE_URL", "https://app.klikk.co.za"),
            },
        )
    except Exception as exc:
        logger.warning("popia: could not send denial email: %s", exc)

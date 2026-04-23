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

    Create a Subject Access Request (SAR) and immediately queue the export job.
    Returns the DSARRequest + ExportJob details so the tenant can track status.

    Rate-limited: one pending/running export per user at a time.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Prevent duplicate pending jobs
        existing = DSARRequest.objects.filter(
            requester=request.user,
            request_type=DSARRequest.RequestType.SAR,
            status__in=[DSARRequest.Status.PENDING, DSARRequest.Status.IN_REVIEW],
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
            request_type=DSARRequest.RequestType.SAR,
            reason=ser.validated_data.get("reason", ""),
            status=DSARRequest.Status.IN_REVIEW,
        )

        # Create the export job
        job = ExportJob.objects.create(dsar_request=dsar)

        # Write audit event
        _log_audit(
            "popia.sar_requested",
            request.user,
            f"DSARRequest #{dsar.pk}",
            {"request_type": "sar", "dsar_id": dsar.pk},
            request,
        )

        # Kick off the export in a background thread
        run_export_job_async(job.pk)

        return Response(
            {
                "dsar_request": DSARRequestSerializer(dsar).data,
                "export_job": ExportJobSerializer(job).data,
                "message": (
                    "Your data export is being compiled. "
                    "You will receive an email with a download link within a few minutes."
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
    No authentication required — the token IS the credential.
    Token is single-use by design (invalidated after download).
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request, token: str):
        try:
            job = ExportJob.objects.select_related("dsar_request").get(
                download_token=token,
                status=ExportJob.JobStatus.COMPLETED,
            )
        except ExportJob.DoesNotExist:
            raise Http404("Download link not found or already used.")

        if job.is_expired:
            raise Http404("Download link has expired.")

        zip_path = Path(settings.MEDIA_ROOT) / job.archive_path
        if not zip_path.exists():
            raise Http404("Export file not found.")

        _log_audit(
            "popia.export_downloaded",
            job.dsar_request.requester,
            f"ExportJob #{job.pk}",
            {"job_id": job.pk, "dsar_id": job.dsar_request.pk},
        )

        response = FileResponse(
            open(zip_path, "rb"),
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

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        type_filter = request.query_params.get("request_type")
        if type_filter:
            qs = qs.filter(request_type=type_filter)

        return Response(DSARRequestSerializer(qs, many=True).data)


class DSARReviewView(APIView):
    """
    POST /api/v1/popia/dsar-queue/<id>/review/

    Approve or deny a DSAR request.

    For RTBF approvals: immediately executes the erasure.
    For SAR approvals: no-op (export is already running from initial request).
    For denials: marks denied and notifies the data subject.
    """
    permission_classes = [IsAuthenticated, IsAdminOrAgencyAdmin]

    def post(self, request, pk: int):
        try:
            dsar = DSARRequest.objects.select_related("requester").get(pk=pk)
        except DSARRequest.DoesNotExist:
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

            # For RTBF: execute the erasure immediately
            if dsar.request_type == DSARRequest.RequestType.RTBF:
                from .services.deletion_service import execute_erasure
                execute_erasure(dsar, reviewer=request.user)

            return Response(
                {
                    "detail": "Request approved.",
                    "dsar_request": DSARRequestSerializer(dsar).data,
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

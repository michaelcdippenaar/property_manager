"""
apps/popia/services/export_service.py

POPIA s23 Data Export Service.

Compiles a data subject's full personal information held across all Klikk
subsystems into a ZIP archive:

  data_export_<user_id>_<timestamp>/
    profile.json          — User + Person profile fields
    leases.json           — Lease records where user is a party
    payments.json         — Payment records linked to the user's leases
    maintenance.json      — Maintenance tickets submitted by or assigned to the user
    audit_events.json     — AuditEvent rows where user is actor OR the data subject (GFK target)
    otp_audit.json        — OTP verification audit trail (OTPAuditLog)
    otp_codes.json        — OTP code records metadata (OTPCodeV1, no code hashes)
    README.txt            — Human-readable index and POPIA statement

The ZIP is written to MEDIA_ROOT/popia_exports/<job_id>.zip and the ExportJob
record is updated on completion or failure.

After the job completes an email with a signed download link is sent to the
data subject.

This module is designed to be called synchronously from a management command or
a Django-Q / Celery task.  The view creates the ExportJob(queued) and immediately
calls `run_export_job()` in a thread — good enough for v1 with low request volume.
For high volume, wire to a proper task queue.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
import zipfile
from datetime import date
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_RETENTION_STATEMENT = """\
POPIA s23 — Data Export
=======================
This archive contains all personal information held by Klikk about you as a
data subject, in accordance with section 23 of the Protection of Personal
Information Act 4 of 2013 (POPIA).

RETENTION RULES (why some records are retained even after erasure):
  - Lease records: 5 years post-termination (FICA s22 / RHA)
  - Payment records: 7 years (SARS / Income Tax Act)
  - Audit events: 5 years minimum (FICA s22 / RHA)

INFORMATION OFFICER: privacy@klikk.co.za
Date generated: {generated_at}
"""


def _safe_json(obj):
    """JSON serialiser that handles Decimal, date/datetime, UUID."""
    import decimal
    import datetime
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _qs_to_list(qs, fields: list[str]) -> list[dict]:
    return list(qs.values(*fields))


def _compile_profile(user) -> dict:
    """Compile User + linked Person profile data."""
    data: dict = {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "id_number": user.id_number,
        "role": user.role,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "is_active": user.is_active,
    }
    try:
        person = user.person_profile
        data["person_profile"] = {
            "full_name": person.full_name,
            "person_type": person.person_type,
            "id_number": person.id_number,
            "phone": person.phone,
            "email": person.email,
            "address": person.address,
            "employer": person.employer,
            "occupation": person.occupation,
            "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
            "emergency_contact_name": person.emergency_contact_name,
            "emergency_contact_phone": person.emergency_contact_phone,
            "monthly_income": str(person.monthly_income) if person.monthly_income else None,
        }
    except Exception:
        data["person_profile"] = None
    return data


def _compile_leases(user) -> list[dict]:
    """Compile lease records where user is a party (via Person profile)."""
    try:
        from apps.leases.models import Lease
        person = getattr(user, "person_profile", None)
        if person is None:
            return []
        fields = [
            "id", "status", "start_date", "end_date", "monthly_rent",
            "deposit_amount", "created_at", "property__address",
        ]
        qs = Lease.objects.filter(
            leaseparty__person=person
        ).distinct().values(*fields)
        return list(qs)
    except Exception as exc:
        logger.warning("popia export: leases query failed: %s", exc)
        return []


def _compile_payments(user) -> list[dict]:
    """Compile payment records linked to the user's leases."""
    try:
        from apps.payments.models import RentPayment
        person = getattr(user, "person_profile", None)
        if person is None:
            return []
        from apps.leases.models import Lease
        lease_ids = Lease.objects.filter(
            leaseparty__person=person
        ).distinct().values_list("id", flat=True)
        fields = [
            "id", "lease_id", "amount", "payment_date", "status",
            "payment_method", "reference", "created_at",
        ]
        qs = RentPayment.objects.filter(lease_id__in=lease_ids).values(*fields)
        return list(qs)
    except Exception as exc:
        logger.warning("popia export: payments query failed: %s", exc)
        return []


def _compile_maintenance(user) -> list[dict]:
    """Compile maintenance tickets submitted by the user."""
    try:
        from apps.maintenance.models import MaintenanceRequest
        fields = [
            "id", "title", "description", "status", "category",
            "priority", "created_at", "resolved_at", "property__address",
        ]
        qs = MaintenanceRequest.objects.filter(
            submitted_by=user
        ).values(*fields)
        return list(qs)
    except Exception as exc:
        logger.warning("popia export: maintenance query failed: %s", exc)
        return []


def _compile_audit_events(user) -> list[dict]:
    """
    Compile audit events where user is the actor OR the data subject.

    "Data subject" events are rows where the GFK target is the User record
    itself (content_type = accounts.User, object_id = user.pk).  These cover
    role-change events, account-creation events, and any POPIA action logged
    against the user account.
    """
    try:
        from django.contrib.contenttypes.models import ContentType
        from apps.audit.models import AuditEvent
        from apps.accounts.models import User as UserModel

        fields = [
            "id", "action", "target_repr", "ip_address",
            "user_agent", "timestamp", "actor_id", "actor_email",
        ]

        # Events where user was the actor
        actor_qs = AuditEvent.objects.filter(actor=user).values(*fields)

        # Events where user's account is the target object (data subject)
        try:
            user_ct = ContentType.objects.get_for_model(UserModel)
            subject_qs = AuditEvent.objects.filter(
                content_type=user_ct,
                object_id=user.pk,
            ).exclude(actor=user).values(*fields)
        except Exception:
            subject_qs = AuditEvent.objects.none()

        # Combine, de-duplicate by id
        combined = {row["id"]: row for row in actor_qs}
        for row in subject_qs:
            combined.setdefault(row["id"], row)

        return list(combined.values())
    except Exception as exc:
        logger.warning("popia export: audit query failed: %s", exc)
        return []


def _compile_otp_audit(user) -> list[dict]:
    """Compile OTP verification audit trail (OTPAuditLog) for the user."""
    try:
        from apps.accounts.models import OTPAuditLog
        fields = ["id", "purpose", "event_type", "channel", "metadata", "created_at"]
        return list(OTPAuditLog.objects.filter(user=user).values(*fields))
    except Exception as exc:
        logger.warning("popia export: otp_audit query failed: %s", exc)
        return []


def _compile_otp_codes(user) -> list[dict]:
    """Compile OTPCodeV1 records (metadata only — no code hashes) for the user."""
    try:
        from apps.accounts.models import OTPCodeV1
        # Exclude code_hash — it is a security artefact, not personal data
        fields = [
            "id", "purpose", "channel_used", "created_at",
            "expires_at", "consumed_at", "attempt_count",
        ]
        return list(OTPCodeV1.objects.filter(user=user).values(*fields))
    except Exception as exc:
        logger.warning("popia export: otp_codes query failed: %s", exc)
        return []


def build_export_zip(user, job_id: int) -> Path:
    """
    Compile all personal data for `user` and write a ZIP to MEDIA_ROOT/popia_exports/.

    Returns the absolute path to the ZIP file.
    Raises on any unrecoverable error.
    """
    exports_dir = Path(settings.MEDIA_ROOT) / "popia_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    zip_path = exports_dir / f"{job_id}.zip"
    generated_at = timezone.now().isoformat()

    profile = _compile_profile(user)
    leases = _compile_leases(user)
    payments = _compile_payments(user)
    maintenance = _compile_maintenance(user)
    audit_events = _compile_audit_events(user)
    otp_audit = _compile_otp_audit(user)
    otp_codes = _compile_otp_codes(user)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("profile.json", json.dumps(profile, default=_safe_json, indent=2))
        zf.writestr("leases.json", json.dumps(leases, default=_safe_json, indent=2))
        zf.writestr("payments.json", json.dumps(payments, default=_safe_json, indent=2))
        zf.writestr("maintenance.json", json.dumps(maintenance, default=_safe_json, indent=2))
        zf.writestr("audit_events.json", json.dumps(audit_events, default=_safe_json, indent=2))
        zf.writestr("otp_audit.json", json.dumps(otp_audit, default=_safe_json, indent=2))
        zf.writestr("otp_codes.json", json.dumps(otp_codes, default=_safe_json, indent=2))
        zf.writestr(
            "README.txt",
            _RETENTION_STATEMENT.format(generated_at=generated_at),
        )

    return zip_path


def run_export_job(job_pk: int) -> None:
    """
    Execute an ExportJob identified by `job_pk`.

    Updates job.status to running, then completed (or failed).
    Sends an email with the download link on success.
    Safe to call from a background thread.
    """
    from apps.popia.models import ExportJob

    try:
        job = ExportJob.objects.select_related(
            "dsar_request__requester"
        ).get(pk=job_pk)
    except ExportJob.DoesNotExist:
        logger.error("run_export_job: ExportJob %s not found", job_pk)
        return

    job.status = ExportJob.JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    user = job.dsar_request.requester
    if user is None:
        job.status = ExportJob.JobStatus.FAILED
        job.error_detail = "User account no longer exists."
        job.save(update_fields=["status", "error_detail", "updated_at"])
        return

    try:
        zip_path = build_export_zip(user, job_pk)
        # Store path relative to MEDIA_ROOT
        rel_path = str(zip_path.relative_to(settings.MEDIA_ROOT))
        job.archive_path = rel_path
        job.status = ExportJob.JobStatus.COMPLETED
        job.dsar_request.status = job.dsar_request.Status.COMPLETED
        job.dsar_request.completed_at = timezone.now()
        job.dsar_request.save(update_fields=["status", "completed_at", "updated_at"])
        job.save(update_fields=["archive_path", "status", "updated_at"])

        _send_download_email(job)
    except Exception as exc:
        logger.exception("run_export_job: export failed for job %s", job_pk)
        job.status = ExportJob.JobStatus.FAILED
        job.error_detail = str(exc)
        job.save(update_fields=["status", "error_detail", "updated_at"])


def _send_download_email(job) -> None:
    """Send the signed download link email to the data subject."""
    try:
        from apps.notifications.services.email import send_template_email

        base_url = getattr(settings, "FRONTEND_BASE_URL", "https://app.klikk.co.za")
        download_url = f"{base_url}/popia/download/{job.download_token}/"

        send_template_email(
            template_id="popia_export_ready",
            to_emails=job.dsar_request.requester_email,
            context={
                "recipient_name": job.dsar_request.requester.full_name
                if job.dsar_request.requester
                else "Data Subject",
                "download_url": download_url,
                "expires_at": job.expires_at.strftime("%d %B %Y at %H:%M UTC"),
                "cta_url": download_url,
            },
        )
    except Exception as exc:
        logger.warning("popia export: could not send download email: %s", exc)


def run_export_job_async(job_pk: int) -> None:
    """Spawn a daemon thread to run the export job (v1 low-volume approach)."""
    t = threading.Thread(target=run_export_job, args=(job_pk,), daemon=True)
    t.start()

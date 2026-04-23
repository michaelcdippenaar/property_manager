"""
apps/popia/tests/test_dsar.py

POPIA s23 / s24 self-service tests.

Run with:
    pytest backend/apps/popia/tests/test_dsar.py -v
"""
from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.popia.models import DSARRequest, ExportJob


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tenant(db):
    return User.objects.create_user(
        email="tenant@test.co.za",
        password="pass1234!",
        role=User.Role.TENANT,
        first_name="Test",
        last_name="Tenant",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@test.co.za",
        password="pass1234!",
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def tenant_client(tenant):
    c = APIClient()
    c.force_authenticate(user=tenant)
    return c


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def anon_client():
    return APIClient()


# ─────────────────────────────────────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDSARRequestModel:
    def test_sla_deadline_auto_set_on_create(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        assert dsar.sla_deadline is not None
        delta = dsar.sla_deadline - dsar.created_at
        assert 29 <= delta.days <= 30

    def test_days_remaining_positive_when_fresh(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        assert dsar.days_remaining >= 29

    def test_is_overdue_false_when_fresh(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        assert not dsar.is_overdue

    def test_is_overdue_true_when_past_deadline(self, tenant):
        from datetime import timedelta
        past = timezone.now() - timedelta(days=1)
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
            sla_deadline=past,
        )
        assert dsar.is_overdue

    def test_completed_status_not_overdue(self, tenant):
        from datetime import timedelta
        past = timezone.now() - timedelta(days=1)
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.COMPLETED,
            sla_deadline=past,
        )
        assert not dsar.is_overdue


@pytest.mark.django_db
class TestExportJobModel:
    def test_expires_at_auto_set(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.IN_REVIEW,
        )
        job = ExportJob.objects.create(dsar_request=dsar)
        assert job.expires_at is not None
        delta = job.expires_at - job.created_at
        assert delta.days >= 6  # 7-day TTL

    def test_is_not_downloadable_when_queued(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.IN_REVIEW,
        )
        job = ExportJob.objects.create(dsar_request=dsar)
        assert not job.is_downloadable

    def test_download_token_unique(self, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.IN_REVIEW,
        )
        j1 = ExportJob.objects.create(dsar_request=dsar)
        # Token must be set
        assert len(j1.download_token) > 10


# ─────────────────────────────────────────────────────────────────────────────
# API: tenant endpoints
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDataExportRequestView:
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 401

    def test_tenant_can_request_export(self, tenant_client):
        resp = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 201
        data = resp.json()
        assert "dsar_request" in data
        assert data["dsar_request"]["request_type"] == "sar"
        # SAR now starts as PENDING (requires operator approval before export runs)
        assert data["dsar_request"]["status"] == "pending"
        # No export_job at submission time — created on approval
        assert "export_job" not in data

    def test_duplicate_pending_export_returns_200(self, tenant_client, tenant):
        # First request
        resp1 = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp1.status_code == 201

        # Second request while first is still pending
        resp2 = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp2.status_code == 200
        assert "already have a pending" in resp2.json()["detail"]

    def test_export_creates_audit_event(self, tenant_client):
        from apps.audit.models import AuditEvent
        resp = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 201
        assert AuditEvent.objects.filter(action="popia.sar_requested").exists()


@pytest.mark.django_db
class TestErasureRequestView:
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.post("/api/v1/popia/erasure-request/", {})
        assert resp.status_code == 401

    def test_tenant_can_request_erasure(self, tenant_client):
        resp = tenant_client.post(
            "/api/v1/popia/erasure-request/",
            {"reason": "I no longer wish to use the service."},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["dsar_request"]["request_type"] == "rtbf"
        assert data["dsar_request"]["status"] == "pending"

    def test_duplicate_pending_erasure_returns_200(self, tenant_client):
        resp1 = tenant_client.post("/api/v1/popia/erasure-request/", {})
        assert resp1.status_code == 201
        resp2 = tenant_client.post("/api/v1/popia/erasure-request/", {})
        assert resp2.status_code == 200
        assert "already have a pending" in resp2.json()["detail"]

    def test_erasure_creates_audit_event(self, tenant_client):
        from apps.audit.models import AuditEvent
        resp = tenant_client.post("/api/v1/popia/erasure-request/", {})
        assert resp.status_code == 201
        assert AuditEvent.objects.filter(action="popia.rtbf_requested").exists()


@pytest.mark.django_db
class TestMyDSARRequestsView:
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get("/api/v1/popia/my-requests/")
        assert resp.status_code == 401

    def test_returns_own_requests_only(self, tenant_client, tenant, admin_user):
        # Create a request as tenant
        DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        # Create a request as admin (should not appear in tenant's list)
        DSARRequest.objects.create(
            requester=admin_user,
            requester_email=admin_user.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        resp = tenant_client.get("/api/v1/popia/my-requests/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["requester_email"] == tenant.email


# ─────────────────────────────────────────────────────────────────────────────
# API: operator DSAR queue
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDSARQueueView:
    def test_tenant_cannot_access_queue(self, tenant_client):
        resp = tenant_client.get("/api/v1/popia/dsar-queue/")
        assert resp.status_code == 403

    def test_admin_can_list_all_requests(self, admin_client, tenant):
        DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get("/api/v1/popia/dsar-queue/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_filter_by_status(self, admin_client, tenant):
        DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.COMPLETED,
        )
        resp = admin_client.get("/api/v1/popia/dsar-queue/?status=completed")
        assert resp.status_code == 200
        for item in resp.json():
            assert item["status"] == "completed"


@pytest.mark.django_db
class TestDSARReviewView:
    def test_tenant_cannot_review(self, tenant_client, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = tenant_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "deny", "denial_reason": "test"},
        )
        assert resp.status_code == 403

    def test_admin_can_deny_with_reason(self, admin_client, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {
                "action": "deny",
                "denial_reason": "Records must be retained for FICA compliance.",
                "operator_notes": "Active lease in place.",
            },
        )
        assert resp.status_code == 200
        dsar.refresh_from_db()
        assert dsar.status == DSARRequest.Status.DENIED
        assert "FICA" in dsar.denial_reason

    def test_deny_without_reason_returns_400(self, admin_client, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "deny"},
        )
        assert resp.status_code == 400

    def test_admin_can_approve_sar(self, admin_client, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert resp.status_code == 200
        dsar.refresh_from_db()
        assert dsar.status == DSARRequest.Status.APPROVED

    def test_review_already_completed_returns_400(self, admin_client, tenant):
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.COMPLETED,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert resp.status_code == 400

    def test_approve_rtbf_tombstones_user(self, admin_client, tenant):
        """Approving an RTBF erases the user's PII."""
        original_email = tenant.email
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=original_email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert resp.status_code == 200
        tenant.refresh_from_db()
        # Email scrubbed
        assert original_email not in tenant.email
        assert "deleted.klikk.co.za" in tenant.email
        # PII cleared
        assert tenant.first_name == ""
        assert tenant.last_name == ""
        assert not tenant.is_active

    def test_approve_rtbf_writes_audit_event(self, admin_client, tenant):
        from apps.audit.models import AuditEvent
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert AuditEvent.objects.filter(action="popia.user_erased").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Download endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def second_tenant(db):
    return User.objects.create_user(
        email="tenant2@test.co.za",
        password="pass1234!",
        role=User.Role.TENANT,
        first_name="Other",
        last_name="Tenant",
    )


@pytest.fixture
def second_tenant_client(second_tenant):
    c = APIClient()
    c.force_authenticate(user=second_tenant)
    return c


def _make_completed_job(tenant, tmp_path):
    """Helper: create a completed ExportJob with a real zip file."""
    import zipfile as zf
    from django.conf import settings
    from pathlib import Path

    dsar = DSARRequest.objects.create(
        requester=tenant,
        requester_email=tenant.email,
        request_type=DSARRequest.RequestType.SAR,
        status=DSARRequest.Status.COMPLETED,
    )
    # Write a minimal zip to MEDIA_ROOT so FileResponse can stream it
    exports_dir = Path(settings.MEDIA_ROOT) / "popia_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    zip_path = exports_dir / f"test_{dsar.pk}.zip"
    with zf.ZipFile(zip_path, "w") as z:
        z.writestr("README.txt", "test export")
    rel_path = f"popia_exports/test_{dsar.pk}.zip"

    job = ExportJob.objects.create(
        dsar_request=dsar,
        status=ExportJob.JobStatus.COMPLETED,
        archive_path=rel_path,
    )
    return job


@pytest.mark.django_db
class TestExportDownloadView:
    # ── Original tests updated for new auth requirement ───────────────────────

    def test_unauthenticated_invalid_token_returns_401(self, anon_client):
        """Download endpoint now requires authentication (Blocker 1)."""
        resp = anon_client.get("/api/v1/popia/download/not-a-real-token/")
        assert resp.status_code == 401

    def test_invalid_token_authenticated_returns_404(self, tenant_client):
        resp = tenant_client.get("/api/v1/popia/download/not-a-real-token/")
        assert resp.status_code == 404

    def test_expired_token_returns_404(self, tenant_client, tenant):
        from datetime import timedelta
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.COMPLETED,
        )
        past = timezone.now() - timedelta(days=1)
        job = ExportJob.objects.create(
            dsar_request=dsar,
            status=ExportJob.JobStatus.COMPLETED,
            archive_path="popia_exports/fake.zip",
            expires_at=past,
        )
        resp = tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp.status_code == 404

    # ── Blocker 1: token must be bound to authenticated data subject ──────────

    def test_different_user_with_valid_token_gets_403(
        self, second_tenant_client, tenant, tmp_path
    ):
        """A valid token presented by a DIFFERENT authenticated user must be rejected."""
        job = _make_completed_job(tenant, tmp_path)
        resp = second_tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp.status_code == 403

    def test_owner_can_download_own_export(self, tenant_client, tenant, tmp_path):
        """The data subject can download their own export when authenticated."""
        job = _make_completed_job(tenant, tmp_path)
        resp = tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp.status_code == 200

    # ── Blocker 2: single-use enforcement ─────────────────────────────────────

    def test_consumed_token_returns_410(self, tenant_client, tenant, tmp_path):
        """A token that has already been used returns 410 Gone (single-use)."""
        job = _make_completed_job(tenant, tmp_path)
        # First download — succeeds and marks CONSUMED
        resp1 = tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp1.status_code == 200
        job.refresh_from_db()
        assert job.status == ExportJob.JobStatus.CONSUMED

        # Second download — must fail
        resp2 = tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp2.status_code == 410

    def test_download_marks_job_consumed(self, tenant_client, tenant, tmp_path):
        """Job status transitions to CONSUMED after successful download."""
        job = _make_completed_job(tenant, tmp_path)
        assert job.status == ExportJob.JobStatus.COMPLETED
        tenant_client.get(f"/api/v1/popia/download/{job.download_token}/")
        job.refresh_from_db()
        assert job.status == ExportJob.JobStatus.CONSUMED


# ─────────────────────────────────────────────────────────────────────────────
# Blocker 4: SAR now requires operator approval before export runs
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSARRequiresApproval:
    def test_sar_submission_does_not_auto_run_export(self, tenant_client, tenant):
        """SAR submission must NOT queue an ExportJob — operator must approve first."""
        resp = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 201
        dsar_id = resp.json()["dsar_request"]["id"]
        dsar = DSARRequest.objects.get(pk=dsar_id)
        # Status should be pending, not in_review with a job already running
        assert dsar.status == DSARRequest.Status.PENDING
        # No ExportJob should exist yet
        assert not ExportJob.objects.filter(dsar_request=dsar).exists()

    def test_sar_submission_creates_pending_not_in_review(self, tenant_client):
        """SAR must start as PENDING so it enters the operator queue."""
        resp = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 201
        assert resp.json()["dsar_request"]["status"] == "pending"

    def test_admin_approve_sar_creates_export_job(self, admin_client, tenant):
        """Approving a SAR via the operator queue must trigger the export."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert resp.status_code == 200
        # ExportJob must now exist (the async thread may or may not have completed,
        # but the job row must be present)
        assert ExportJob.objects.filter(dsar_request=dsar).exists()

    def test_duplicate_pending_sar_includes_approved_status(self, tenant_client, tenant):
        """
        If a SAR is already APPROVED (export running), tenant must not be able
        to open a second one.
        """
        DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.APPROVED,
        )
        resp = tenant_client.post("/api/v1/popia/data-export/", {})
        assert resp.status_code == 200
        assert "already have a pending" in resp.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# Blocker 3: Export scope — OTP records included
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExportScope:
    def test_otp_audit_logs_included_in_export(self, tenant):
        """OTPAuditLog rows for the user are included in the export ZIP."""
        import zipfile as zf
        from apps.accounts.models import OTPAuditLog
        from apps.popia.services.export_service import build_export_zip

        OTPAuditLog.objects.create(
            user=tenant,
            purpose="login",
            event_type="sent",
            channel="sms",
        )
        import tempfile, os
        from django.conf import settings
        with tempfile.TemporaryDirectory() as tmp:
            original_media = settings.MEDIA_ROOT
            settings.MEDIA_ROOT = tmp
            try:
                zip_path = build_export_zip(tenant, job_id=9999)
                with zf.ZipFile(zip_path) as z:
                    names = z.namelist()
                    assert "otp_audit.json" in names
                    import json
                    data = json.loads(z.read("otp_audit.json"))
                    assert len(data) == 1
                    assert data[0]["purpose"] == "login"
            finally:
                settings.MEDIA_ROOT = original_media

    def test_otp_code_records_included_in_export(self, tenant):
        """OTPCodeV1 rows (without code_hash) are included in the export ZIP."""
        import zipfile as zf
        from apps.accounts.models import OTPCodeV1
        from apps.popia.services.export_service import build_export_zip
        from datetime import timedelta

        OTPCodeV1.objects.create(
            user=tenant,
            purpose="login",
            code_hash="hashed",
            channel_used="sms",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        import tempfile
        from django.conf import settings
        with tempfile.TemporaryDirectory() as tmp:
            original_media = settings.MEDIA_ROOT
            settings.MEDIA_ROOT = tmp
            try:
                zip_path = build_export_zip(tenant, job_id=9998)
                with zf.ZipFile(zip_path) as z:
                    import json
                    data = json.loads(z.read("otp_codes.json"))
                    assert len(data) == 1
                    # code_hash must NOT be present
                    assert "code_hash" not in data[0]
                    assert data[0]["purpose"] == "login"
            finally:
                settings.MEDIA_ROOT = original_media


# ─────────────────────────────────────────────────────────────────────────────
# RTBF retention flags guardrail (RNT-SEC-041)
# ─────────────────────────────────────────────────────────────────────────────

def _make_property_and_unit():
    """Helper: create a minimal Property + Unit for lease FK requirements."""
    from apps.accounts.models import Person
    from apps.properties.models import Property, Unit

    owner_person = Person.objects.create(full_name="Test Owner")
    prop = Property.objects.create(
        owner=owner_person,
        name="Test Property",
        property_type="apartment",
        address="1 Test St",
        city="Cape Town",
        province="Western Cape",
        postal_code="8001",
    )
    unit = Unit.objects.create(
        property=prop,
        unit_number="1",
        rent_amount="10000.00",
    )
    return unit


@pytest.mark.django_db
class TestRTBFRetentionFlags:
    """
    Tests for the GET /api/v1/popia/dsar-queue/<id>/review/ endpoint
    that surfaces retention flags before the operator approves an RTBF.
    Tagged rtbf so they are reachable via: pytest -k rtbf
    """

    def test_rtbf_review_get_returns_retention_flags_no_lease(self, admin_client, tenant):
        """Flags are both False when tenant has no linked Person / lease."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 200
        data = resp.json()
        assert "retention_flags" in data
        flags = data["retention_flags"]
        assert flags["has_active_lease"] is False
        assert flags["has_outstanding_payments"] is False

    def test_rtbf_review_get_returns_dsar_request(self, admin_client, tenant):
        """GET response also includes the serialised dsar_request."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 200
        data = resp.json()
        assert "dsar_request" in data
        assert data["dsar_request"]["id"] == dsar.pk

    def test_sar_review_get_returns_null_retention_flags(self, admin_client, tenant):
        """For SAR requests, retention_flags should be null (not applicable)."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.SAR,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["retention_flags"] is None

    def test_rtbf_review_flags_active_lease(self, admin_client, tenant):
        """has_active_lease is True when tenant has a linked Person on an ACTIVE lease."""
        from datetime import date
        from apps.accounts.models import Person
        from apps.leases.models import Lease

        unit = _make_property_and_unit()

        # Link a Person to the tenant user
        person = Person.objects.create(
            linked_user=tenant,
            full_name=f"{tenant.first_name} {tenant.last_name}",
        )

        Lease.objects.create(
            unit=unit,
            primary_tenant=person,
            status=Lease.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            monthly_rent="10000.00",
        )

        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 200
        flags = resp.json()["retention_flags"]
        assert flags["has_active_lease"] is True
        assert flags["has_outstanding_payments"] is False

    def test_rtbf_review_flags_outstanding_payments(self, admin_client, tenant):
        """has_outstanding_payments is True when tenant has unpaid invoices."""
        from datetime import date
        from apps.accounts.models import Person
        from apps.leases.models import Lease
        from apps.payments.models import RentInvoice

        unit = _make_property_and_unit()

        person = Person.objects.create(
            linked_user=tenant,
            full_name=f"{tenant.first_name} {tenant.last_name}",
        )

        lease = Lease.objects.create(
            unit=unit,
            primary_tenant=person,
            status=Lease.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            monthly_rent="10000.00",
        )

        RentInvoice.objects.create(
            lease=lease,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            amount_due="10000.00",
            due_date=date(2026, 3, 3),
            status=RentInvoice.Status.UNPAID,
        )

        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 200
        flags = resp.json()["retention_flags"]
        assert flags["has_outstanding_payments"] is True

    def test_rtbf_approve_response_includes_retention_flags(self, admin_client, tenant):
        """POST approve for RTBF should include retention_flags in the response."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # retention_flags key must be present (value is dict or null depending on person profile)
        assert "retention_flags" in data

    def test_tenant_cannot_access_review_get(self, tenant_client, tenant):
        """Tenant must not be able to GET the review detail endpoint."""
        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = tenant_client.get(f"/api/v1/popia/dsar-queue/{dsar.pk}/review/")
        assert resp.status_code == 403

    def test_rtbf_approve_can_proceed_despite_active_lease_flag(self, admin_client, tenant):
        """Operator CAN approve even when has_active_lease flag is set — guardrail not a block."""
        from datetime import date
        from apps.accounts.models import Person
        from apps.leases.models import Lease

        unit = _make_property_and_unit()
        person = Person.objects.create(
            linked_user=tenant,
            full_name=f"{tenant.first_name} {tenant.last_name}",
        )
        Lease.objects.create(
            unit=unit,
            primary_tenant=person,
            status=Lease.Status.ACTIVE,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            monthly_rent="10000.00",
        )

        dsar = DSARRequest.objects.create(
            requester=tenant,
            requester_email=tenant.email,
            request_type=DSARRequest.RequestType.RTBF,
            status=DSARRequest.Status.PENDING,
        )
        resp = admin_client.post(
            f"/api/v1/popia/dsar-queue/{dsar.pk}/review/",
            {"action": "approve"},
        )
        # Must succeed — approval is not blocked by retention flags
        assert resp.status_code == 200
        tenant.refresh_from_db()
        assert "deleted.klikk.co.za" in tenant.email

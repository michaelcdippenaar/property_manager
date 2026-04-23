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
        assert "export_job" in data
        assert data["dsar_request"]["request_type"] == "sar"
        assert data["dsar_request"]["status"] == "in_review"

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

@pytest.mark.django_db
class TestExportDownloadView:
    def test_invalid_token_returns_404(self, anon_client):
        resp = anon_client.get("/api/v1/popia/download/not-a-real-token/")
        assert resp.status_code == 404

    def test_expired_token_returns_404(self, anon_client, tenant):
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
        resp = anon_client.get(f"/api/v1/popia/download/{job.download_token}/")
        assert resp.status_code == 404

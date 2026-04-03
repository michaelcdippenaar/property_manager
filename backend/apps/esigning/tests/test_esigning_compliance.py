"""
Tests for e-signing and authentication audit compliance.

P7: ESigningAuditEvent model and log_esigning_event helper
P8: AuthAuditLog creation via auth API endpoints
"""
from django.urls import reverse

from apps.accounts.models import AuthAuditLog
from apps.esigning.audit import log_esigning_event
from apps.esigning.models import ESigningAuditEvent, ESigningSubmission
from tests.base import TremlyAPITestCase


class ESigningAuditEventModelTests(TremlyAPITestCase):
    """P7 — ESigningAuditEvent can be created with all fields and event types
    match ECTA compliance requirements."""

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.lease = self.create_lease()
        self.submission = ESigningSubmission.objects.create(
            lease=self.lease,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signing_mode="sequential",
            document_html="<p>Test lease</p>",
            signers=[
                {"role": "tenant_1", "name": "Test Tenant", "email": "tenant@test.com"},
                {"role": "landlord", "name": "Test Landlord", "email": "agent@test.com"},
            ],
            created_by=self.agent,
        )

    def test_create_audit_event_all_fields(self):
        """ESigningAuditEvent can be created with every field populated."""
        event = ESigningAuditEvent.objects.create(
            submission=self.submission,
            signer_role="tenant_1",
            event_type=ESigningAuditEvent.EventType.SIGNATURE_APPLIED,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Test",
            user=self.tenant,
            metadata={"field": "signature_tenant_1", "page": 3},
        )
        event.refresh_from_db()
        self.assertEqual(event.submission, self.submission)
        self.assertEqual(event.signer_role, "tenant_1")
        self.assertEqual(event.event_type, "signature_applied")
        self.assertEqual(event.ip_address, "192.168.1.1")
        self.assertEqual(event.user_agent, "Mozilla/5.0 Test")
        self.assertEqual(event.user, self.tenant)
        self.assertEqual(event.metadata["field"], "signature_tenant_1")
        self.assertIsNotNone(event.created_at)

    def test_event_types_cover_ecta_requirements(self):
        """All ECTA Section 13 compliance event types are defined."""
        required_types = {
            "link_created",
            "document_viewed",
            "consent_given",
            "signature_applied",
            "signing_completed",
            "document_completed",
            "link_expired",
        }
        actual_types = {choice[0] for choice in ESigningAuditEvent.EventType.choices}
        self.assertEqual(required_types, actual_types)

    def test_log_esigning_event_helper_creates_event(self):
        """log_esigning_event() creates an audit event with correct fields."""
        event = log_esigning_event(
            submission=self.submission,
            event_type=ESigningAuditEvent.EventType.DOCUMENT_VIEWED,
            signer_role="tenant_1",
            user=self.tenant,
            metadata={"source": "public_link"},
        )
        self.assertIsInstance(event, ESigningAuditEvent)
        self.assertEqual(event.event_type, "document_viewed")
        self.assertEqual(event.signer_role, "tenant_1")
        self.assertEqual(event.user, self.tenant)
        self.assertEqual(event.metadata, {"source": "public_link"})
        # No request passed — ip_address should be None
        self.assertIsNone(event.ip_address)
        self.assertEqual(event.user_agent, "")

    def test_log_esigning_event_with_request_extracts_ip_and_ua(self):
        """log_esigning_event() extracts IP and User-Agent from a request object."""
        factory = self.client_class()
        request = factory.get("/fake/").wsgi_request
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        request.META["HTTP_USER_AGENT"] = "TestAgent/1.0"

        event = log_esigning_event(
            submission=self.submission,
            event_type=ESigningAuditEvent.EventType.CONSENT_GIVEN,
            request=request,
            signer_role="landlord",
        )
        self.assertEqual(event.ip_address, "10.0.0.1")
        self.assertEqual(event.user_agent, "TestAgent/1.0")

    def test_audit_events_ordered_by_created_at(self):
        """Audit events are returned in chronological order."""
        e1 = log_esigning_event(
            self.submission, ESigningAuditEvent.EventType.LINK_CREATED, signer_role="tenant_1",
        )
        e2 = log_esigning_event(
            self.submission, ESigningAuditEvent.EventType.DOCUMENT_VIEWED, signer_role="tenant_1",
        )
        e3 = log_esigning_event(
            self.submission, ESigningAuditEvent.EventType.SIGNATURE_APPLIED, signer_role="tenant_1",
        )
        events = list(self.submission.audit_events.all())
        self.assertEqual([e.pk for e in events], [e1.pk, e2.pk, e3.pk])

    def test_str_representation(self):
        """__str__ includes event_type and submission_id."""
        event = log_esigning_event(
            self.submission, ESigningAuditEvent.EventType.SIGNING_COMPLETED, signer_role="tenant_1",
        )
        text = str(event)
        self.assertIn("signing_completed", text)


class AuthAuditLogViaEndpointsTests(TremlyAPITestCase):
    """P8 — Auth endpoints create AuthAuditLog entries for login, register,
    logout, and failed login."""

    def test_register_creates_audit_event(self):
        """POST to auth-register creates a 'register' audit log."""
        url = reverse("auth-register")
        data = {
            "email": "newuser@test.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)

        logs = AuthAuditLog.objects.filter(event_type="register")
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.user.email, "newuser@test.com")

    def test_login_success_creates_audit_event(self):
        """POST to auth-login with valid credentials creates 'login_success' audit log."""
        user = self.create_user(email="logintest@test.com", password="testpass123")
        url = reverse("auth-login")
        data = {"email": "logintest@test.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)

        logs = AuthAuditLog.objects.filter(event_type="login_success")
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.user, user)

    def test_login_failure_creates_audit_event(self):
        """POST to auth-login with bad password creates 'login_failed' audit log."""
        self.create_user(email="failtest@test.com", password="testpass123")
        url = reverse("auth-login")
        data = {"email": "failtest@test.com", "password": "wrongpassword"}
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [400, 401])

        logs = AuthAuditLog.objects.filter(event_type="login_failed")
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        # login_failed logs may not have a user (user not authenticated)
        self.assertEqual(log.metadata.get("email"), "failtest@test.com")

    def test_logout_creates_audit_event(self):
        """POST to auth-logout creates a 'logout' audit log."""
        user = self.create_user(email="logouttest@test.com", password="testpass123")
        tokens = self.get_tokens(user)

        self.authenticate(user)
        url = reverse("auth-logout")
        data = {"refresh": tokens["refresh"]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 204)

        logs = AuthAuditLog.objects.filter(event_type="logout")
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.user, user)

    def test_login_failure_for_nonexistent_user_creates_audit_event(self):
        """Login attempt for a non-existent email still creates 'login_failed' audit log."""
        url = reverse("auth-login")
        data = {"email": "ghost@test.com", "password": "testpass123"}
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [400, 401])

        logs = AuthAuditLog.objects.filter(event_type="login_failed")
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().metadata.get("email"), "ghost@test.com")
        self.assertIsNone(logs.first().user)

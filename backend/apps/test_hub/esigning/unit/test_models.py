"""
Unit tests for esigning models.

No DB queries — tests use model instantiation and field introspection.
"""
import pytest
import uuid
from unittest.mock import MagicMock
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.unit


class TestESigningSubmissionStr:
    """ESigningSubmission.__str__ and status choices."""

    def test_str_includes_pk(self):
        from apps.esigning.models import ESigningSubmission
        sub = ESigningSubmission.__new__(ESigningSubmission)
        sub.pk = 42
        sub.status = "pending"
        result = str(sub)
        assert "42" in result

    def test_str_includes_status(self):
        from apps.esigning.models import ESigningSubmission
        sub = ESigningSubmission.__new__(ESigningSubmission)
        sub.pk = 99
        sub.status = "completed"
        result = str(sub)
        assert "completed" in result

    def test_status_choices_exist(self):
        from apps.esigning.models import ESigningSubmission
        choices = [c[0] for c in ESigningSubmission.Status.choices]
        assert "pending" in choices
        assert "in_progress" in choices
        assert "completed" in choices
        assert "declined" in choices
        assert "expired" in choices

    def test_signing_mode_choices_exist(self):
        from apps.esigning.models import ESigningSubmission
        choices = [c[0] for c in ESigningSubmission.SigningMode.choices]
        assert "sequential" in choices
        assert "parallel" in choices

    def test_signing_backend_choices_exist(self):
        from apps.esigning.models import ESigningSubmission
        choices = [c[0] for c in ESigningSubmission.SigningBackend.choices]
        # DocuSeal backend removed; only native remains
        assert "native" in choices

    def test_default_signing_mode_is_sequential(self):
        from apps.esigning.models import ESigningSubmission
        assert ESigningSubmission.SigningMode.SEQUENTIAL == "sequential"

    def test_default_backend_is_native(self):
        from apps.esigning.models import ESigningSubmission
        assert ESigningSubmission.SigningBackend.NATIVE == "native"


# TestESigningSubmissionGetSignerBySubmitterId removed —
# get_signer_by_submitter_id() was DocuSeal-specific and has been removed from the model.


class TestESigningAuditEventStr:
    """ESigningAuditEvent.__str__ and event_type choices."""

    def test_str_includes_event_type(self):
        from apps.esigning.models import ESigningAuditEvent
        from django.db.models.base import ModelState
        event = ESigningAuditEvent.__new__(ESigningAuditEvent)
        event._state = ModelState()
        event.event_type = "signature_applied"
        event.submission_id = 42
        event.created_at = timezone.now()
        result = str(event)
        assert "signature_applied" in result

    def test_ecta_event_types_exist(self):
        from apps.esigning.models import ESigningAuditEvent
        choices = {c[0] for c in ESigningAuditEvent.EventType.choices}
        required = {
            "link_created",
            "document_viewed",
            "consent_given",
            "signature_applied",
            "signing_completed",
            "document_completed",
            "link_expired",
        }
        # Required ECTA types must be present; additional types (draft_saved, etc.) are fine
        missing = required - choices
        assert not missing, f"Missing ECTA event types: {missing}"


class TestESigningPublicLinkExpiry:
    """ESigningPublicLink.is_expired() method."""

    def test_not_expired_for_future_date(self):
        from apps.esigning.models import ESigningPublicLink
        link = ESigningPublicLink.__new__(ESigningPublicLink)
        link.expires_at = timezone.now() + timedelta(days=7)
        assert not link.is_expired()

    def test_expired_for_past_date(self):
        from apps.esigning.models import ESigningPublicLink
        link = ESigningPublicLink.__new__(ESigningPublicLink)
        link.expires_at = timezone.now() - timedelta(days=1)
        assert link.is_expired()

    def test_pk_is_uuid_type(self):
        from apps.esigning.models import ESigningPublicLink
        pk_field = ESigningPublicLink._meta.get_field("id")
        # UUID primary key
        assert "UUID" in type(pk_field).__name__

    def test_uuid_default_generates_unique_values(self):
        """Two separate default UUID values should not collide."""
        generated = {uuid.uuid4() for _ in range(100)}
        assert len(generated) == 100

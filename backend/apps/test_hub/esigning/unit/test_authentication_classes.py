"""
Unit tests for authentication_classes attribute on public esigning views.

Verifies that all public esigning views have explicit authentication_classes = []
to prevent implicit JWT processing overhead, per RNT-SEC-012.
"""
import pytest
from apps.esigning.views import (
    ESigningPublicSignDetailView,
    ESigningPublicDocumentView,
    ESigningPublicSubmitSignatureView,
    ESigningPublicDraftView,
    ESigningPublicDocumentsView,
)

pytestmark = pytest.mark.unit


class TestPublicViewsHaveNoAuthentication:
    """All public esigning views must explicitly disable authentication."""

    def test_esigning_public_sign_detail_view_has_empty_auth_classes(self):
        """ESigningPublicSignDetailView must have authentication_classes = []."""
        assert hasattr(ESigningPublicSignDetailView, "authentication_classes")
        assert ESigningPublicSignDetailView.authentication_classes == []

    def test_esigning_public_document_view_has_empty_auth_classes(self):
        """ESigningPublicDocumentView must have authentication_classes = []."""
        assert hasattr(ESigningPublicDocumentView, "authentication_classes")
        assert ESigningPublicDocumentView.authentication_classes == []

    def test_esigning_public_submit_signature_view_has_empty_auth_classes(self):
        """ESigningPublicSubmitSignatureView must have authentication_classes = []."""
        assert hasattr(ESigningPublicSubmitSignatureView, "authentication_classes")
        assert ESigningPublicSubmitSignatureView.authentication_classes == []

    def test_esigning_public_draft_view_has_empty_auth_classes(self):
        """ESigningPublicDraftView must have authentication_classes = [] (RNT-SEC-012)."""
        assert hasattr(ESigningPublicDraftView, "authentication_classes")
        assert ESigningPublicDraftView.authentication_classes == []

    def test_esigning_public_documents_view_has_empty_auth_classes(self):
        """ESigningPublicDocumentsView must have authentication_classes = [] (RNT-SEC-012)."""
        assert hasattr(ESigningPublicDocumentsView, "authentication_classes")
        assert ESigningPublicDocumentsView.authentication_classes == []

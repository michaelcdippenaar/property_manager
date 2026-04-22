"""
Integration tests for the legal API views.

Covers:
- GET /api/v1/legal/documents/current/ (public)
- GET /api/v1/legal/pending/ (auth required)
- GET/POST /api/v1/legal/consent/ (auth required)
"""
import pytest
from datetime import date

pytestmark = [pytest.mark.integration, pytest.mark.green]


@pytest.fixture
def legal_setup(db, tremly):
    """Create a current ToS document and an active user."""
    from apps.legal.models import LegalDocument
    doc = LegalDocument.objects.create(
        doc_type="tos",
        version="1.0",
        effective_date=date(2026, 1, 1),
        url="https://klikk.co.za/legal/terms",
        is_current=True,
        requires_re_ack=False,
    )
    agent = tremly.create_agent()
    return {"doc": doc, "agent": agent}


class TestCurrentDocumentsView:
    def test_public_access_returns_current_documents(self, api_client, legal_setup):
        doc = legal_setup["doc"]
        response = api_client.get("/api/v1/legal/documents/current/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(d["id"] == doc.pk for d in data)

    def test_no_current_documents_returns_empty_list(self, db, api_client):
        response = api_client.get("/api/v1/legal/documents/current/")
        assert response.status_code == 200
        assert response.json() == []


class TestPendingConsentsView:
    def test_unauthenticated_returns_401(self, db, api_client):
        response = api_client.get("/api/v1/legal/pending/")
        assert response.status_code == 401

    def test_no_pending_when_none_require_reack(self, api_client, legal_setup):
        agent = legal_setup["agent"]
        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/legal/pending/")
        assert response.status_code == 200
        assert response.json() == []

    def test_pending_returned_when_reack_required(self, db, tremly, api_client):
        from apps.legal.models import LegalDocument
        doc = LegalDocument.objects.create(
            doc_type="tos",
            version="2.0",
            effective_date=date(2026, 3, 1),
            url="https://klikk.co.za/legal/terms",
            is_current=True,
            requires_re_ack=True,
        )
        agent = tremly.create_agent()
        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/legal/pending/")
        assert response.status_code == 200
        data = response.json()
        assert any(d["id"] == doc.pk for d in data)


class TestUserConsentView:
    def test_unauthenticated_returns_401(self, db, api_client):
        response = api_client.post("/api/v1/legal/consent/", {"document": 1})
        assert response.status_code == 401

    def test_post_creates_consent(self, api_client, legal_setup):
        from apps.legal.models import UserConsent
        agent = legal_setup["agent"]
        doc = legal_setup["doc"]
        api_client.force_authenticate(user=agent)
        response = api_client.post("/api/v1/legal/consent/", {"document": doc.pk})
        assert response.status_code == 200
        assert UserConsent.objects.filter(user=agent, document=doc).exists()

    def test_post_consent_idempotent(self, api_client, legal_setup):
        """Posting the same consent twice returns 200 without creating a duplicate."""
        from apps.legal.models import UserConsent
        agent = legal_setup["agent"]
        doc = legal_setup["doc"]
        api_client.force_authenticate(user=agent)
        api_client.post("/api/v1/legal/consent/", {"document": doc.pk})
        api_client.post("/api/v1/legal/consent/", {"document": doc.pk})
        assert UserConsent.objects.filter(user=agent, document=doc).count() == 1

    def test_get_returns_user_consents(self, api_client, legal_setup):
        from apps.legal.models import UserConsent
        agent = legal_setup["agent"]
        doc = legal_setup["doc"]
        UserConsent.objects.create(user=agent, document=doc)
        api_client.force_authenticate(user=agent)
        response = api_client.get("/api/v1/legal/consent/")
        assert response.status_code == 200
        data = response.json()
        assert any(c["document"] == doc.pk for c in data)

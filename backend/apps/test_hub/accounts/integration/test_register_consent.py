"""
Integration tests for POPIA s11 consent recording during registration.

Covers RegisterSerializer._record_consent() via POST /api/v1/auth/register/:
- (a) Valid current LegalDocument IDs → UserConsent rows created with correct
      user, document FK, ip_address, and user_agent values.
- (b) Stale / non-existent tos_document_id → HTTP 201, zero UserConsent rows
      (silent-skip of LegalDocument.DoesNotExist).
"""
import pytest
from datetime import date

pytestmark = [pytest.mark.integration, pytest.mark.green]

REGISTER_URL = "/api/v1/auth/register/"


@pytest.fixture
def current_legal_docs(db):
    """Create current ToS and Privacy Policy LegalDocument rows."""
    from apps.legal.models import LegalDocument
    tos = LegalDocument.objects.create(
        doc_type="tos",
        version="1.0",
        effective_date=date(2026, 1, 1),
        url="https://klikk.co.za/legal/terms",
        is_current=True,
        requires_re_ack=False,
    )
    privacy = LegalDocument.objects.create(
        doc_type="privacy",
        version="1.0",
        effective_date=date(2026, 1, 1),
        url="https://klikk.co.za/legal/privacy",
        is_current=True,
        requires_re_ack=False,
    )
    return {"tos": tos, "privacy": privacy}


class TestRegisterConsent:
    def test_valid_document_ids_create_consent_rows(self, api_client, current_legal_docs):
        """
        (a) Registering with valid current document IDs for both tos_document_id
        and privacy_document_id creates UserConsent rows carrying the correct
        user, document FK, ip_address, and user_agent values.
        """
        from apps.accounts.models import User
        from apps.legal.models import UserConsent

        tos_doc = current_legal_docs["tos"]
        privacy_doc = current_legal_docs["privacy"]

        # Inject REMOTE_ADDR and User-Agent so _record_consent can capture them.
        response = api_client.post(
            REGISTER_URL,
            {
                "email": "consent_test@example.com",
                "password": "Passw0rd!SA",
                "first_name": "Lindi",
                "last_name": "Dlamini",
                "tos_document_id": tos_doc.pk,
                "privacy_document_id": privacy_doc.pk,
            },
            REMOTE_ADDR="10.0.0.1",
            HTTP_USER_AGENT="TestBrowser/1.0",
        )

        assert response.status_code == 201

        user = User.objects.get(email="consent_test@example.com")

        tos_consent = UserConsent.objects.get(user=user, document=tos_doc)
        assert tos_consent.ip_address == "10.0.0.1"
        assert tos_consent.user_agent == "TestBrowser/1.0"

        privacy_consent = UserConsent.objects.get(user=user, document=privacy_doc)
        assert privacy_consent.ip_address == "10.0.0.1"
        assert privacy_consent.user_agent == "TestBrowser/1.0"

    def test_xff_header_used_for_ip_when_present(self, api_client, current_legal_docs):
        """
        When X-Forwarded-For is present, the first IP in the chain is recorded
        rather than REMOTE_ADDR.
        """
        from apps.accounts.models import User
        from apps.legal.models import UserConsent

        tos_doc = current_legal_docs["tos"]

        response = api_client.post(
            REGISTER_URL,
            {
                "email": "xff_test@example.com",
                "password": "Passw0rd!SA",
                "first_name": "Sipho",
                "last_name": "Nkosi",
                "tos_document_id": tos_doc.pk,
            },
            REMOTE_ADDR="192.168.1.1",
            HTTP_X_FORWARDED_FOR="203.0.113.42, 10.0.0.1",
            HTTP_USER_AGENT="AgentMobile/2.0",
        )

        assert response.status_code == 201

        user = User.objects.get(email="xff_test@example.com")
        consent = UserConsent.objects.get(user=user, document=tos_doc)
        assert consent.ip_address == "203.0.113.42"
        assert consent.user_agent == "AgentMobile/2.0"

    def test_stale_document_id_succeeds_with_no_consent_row(self, api_client, db):
        """
        (b) Registering with a non-existent tos_document_id returns HTTP 201
        and creates zero UserConsent rows — guards the silent-skip branch in
        _record_consent() for LegalDocument.DoesNotExist.
        """
        from apps.legal.models import UserConsent

        response = api_client.post(
            REGISTER_URL,
            {
                "email": "stale_consent@example.com",
                "password": "Passw0rd!SA",
                "first_name": "Thabo",
                "last_name": "Mokoena",
                "tos_document_id": 99999,  # does not exist
            },
        )

        assert response.status_code == 201
        assert UserConsent.objects.count() == 0

    def test_no_document_ids_creates_no_consent_rows(self, api_client, db):
        """
        Registering without supplying any document IDs is still valid and
        results in zero UserConsent rows.
        """
        from apps.legal.models import UserConsent

        response = api_client.post(
            REGISTER_URL,
            {
                "email": "no_consent@example.com",
                "password": "Passw0rd!SA",
            },
        )

        assert response.status_code == 201
        assert UserConsent.objects.count() == 0

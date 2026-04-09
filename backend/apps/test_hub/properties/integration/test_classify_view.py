"""
Integration tests for the AI landlord document classifier endpoints.

Source file under test: apps/properties/classify_view.py
  - LandlordClassifyView               — POST /landlords/{pk}/classify/
  - LandlordClassifyRegistrationView   — POST /landlords/{pk}/classify-registration/
  - _encode_file, _call_claude, _patch_landlord helpers

All Claude API calls are mocked so no real Anthropic traffic is made.
Covers:
  - 404 when landlord doesn't exist
  - 400 when no documents uploaded
  - 400 when no readable documents
  - 503 when ANTHROPIC_API_KEY missing
  - 502 on Claude APIError
  - 502 on invalid-JSON responses
  - Markdown fence stripping (```json ... ```)
  - Happy-path auto-patching of name/reg/vat/email/phone/type/address
  - Existing fields are NOT overwritten
  - landlord_type promotion (individual → company) triggers only when current type is individual
  - owned_by_trust flag is propagated
  - classification_data is always persisted
  - Registration-only endpoint variants (no doc → 400, happy path → patches landlord)
"""
import json
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.properties.classify_view import _patch_landlord
from apps.properties.models import Landlord, LandlordDocument
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


CLAUDE_CLIENT_PATH = "apps.properties.classify_view.anthropic.Anthropic"


def _fake_claude_response(text: str):
    block = mock.MagicMock()
    block.text = text
    resp = mock.MagicMock()
    resp.content = [block]
    return resp


def _full_classification(**overrides):
    """Build a realistic classification JSON payload with sensible defaults."""
    payload = {
        "entity_type": "Company",
        "entity_subtype": "Pty Ltd",
        "owned_by_trust": False,
        "trust_entity": None,
        "fica": {
            "status": "complete",
            "documents": [],
            "missing": [],
            "flags": [],
        },
        "cipc": {
            "status": "complete",
            "documents": [],
            "missing": [],
            "flags": [],
        },
        "extracted_data": {
            "company_name": "Golden Wave Properties (Pty) Ltd",
            "registration_number": "2021/123456/07",
            "vat_number": "4123456789",
            "email": "admin@goldenwave.co.za",
            "phone": "0214567890",
            "representative_name": "Sally Agent",
            "representative_id_number": "9001015800087",
            "directors": [{"full_name": "Sally Agent", "id_number": "9001015800087"}],
            "address": "12 Vine Street, Stellenbosch, 7600",
            "tax_number": "",
        },
        "persons_graph": [],
        "classified_at": "2026-04-08T10:00:00Z",
    }
    payload.update(overrides)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper: add a document to a landlord
# ─────────────────────────────────────────────────────────────────────────────
def _attach_doc(landlord, *, name="id_doc.pdf", content=b"%PDF-1.4\nfake"):
    doc = LandlordDocument.objects.create(
        landlord=landlord,
        file=SimpleUploadedFile(name, content, content_type="application/pdf"),
        filename=name,
    )
    return doc


def _attach_registration_doc(landlord, *, name="cipc_cert.pdf", content=b"%PDF-1.4\nfake cipc"):
    landlord.registration_document = SimpleUploadedFile(
        name, content, content_type="application/pdf"
    )
    landlord.registration_document_name = name
    landlord.save(update_fields=["registration_document", "registration_document_name"])


# ─────────────────────────────────────────────────────────────────────────────
# LandlordClassifyView — permission + happy path
# ─────────────────────────────────────────────────────────────────────────────
@override_settings(ANTHROPIC_API_KEY="sk-fake-test")
class LandlordClassifyViewTests(TremlyAPITestCase):
    def setUp(self):
        self.agent = self.create_agent(email="agent@classify.test")
        self.landlord = self.create_landlord(
            name="",
            landlord_type="individual",
            email="",
            phone="",
            vat_number="",
            registration_number="",
            representative_name="",
            representative_id_number="",
            address={},
        )
        self.url = reverse("landlord-classify", args=[self.landlord.pk])

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_tenant_is_forbidden(self):
        self.authenticate(self.create_tenant(email="tenant@classify.test"))
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_missing_landlord_returns_404(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("landlord-classify", args=[999999]))
        self.assertEqual(resp.status_code, 404)

    def test_no_documents_returns_400(self):
        self.authenticate(self.agent)
        # landlord has no documents and no registration_document
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No documents uploaded", resp.data["detail"])

    @override_settings(ANTHROPIC_API_KEY="")
    def test_missing_api_key_returns_503(self):
        self.authenticate(self.agent)
        _attach_doc(self.landlord)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", resp.data["detail"])

    def test_claude_api_error_returns_502(self):
        self.authenticate(self.agent)
        _attach_doc(self.landlord)

        import anthropic
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.side_effect = anthropic.APIError(
                "server down", request=mock.MagicMock(), body=None,
            )
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 502)
        self.assertIn("Claude API error", resp.data["detail"])

    def test_invalid_json_returns_502(self):
        self.authenticate(self.agent)
        _attach_doc(self.landlord)

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response("garbage { not json")
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 502)
        self.assertIn("invalid JSON", resp.data["detail"])

    def test_happy_path_patches_landlord(self):
        self.authenticate(self.agent)
        _attach_doc(self.landlord, name="cor143.pdf")

        classification = _full_classification()
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(
                json.dumps(classification)
            )
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["classification"], classification)
        self.assertIn("name", resp.data["patched_fields"])
        self.assertIn("registration_number", resp.data["patched_fields"])
        self.assertIn("vat_number", resp.data["patched_fields"])
        self.assertIn("classification_data", resp.data["patched_fields"])
        self.assertEqual(resp.data["skipped_files"], [])

        # Landlord row is actually updated
        self.landlord.refresh_from_db()
        self.assertEqual(self.landlord.name, "Golden Wave Properties (Pty) Ltd")
        self.assertEqual(self.landlord.registration_number, "2021/123456/07")
        self.assertEqual(self.landlord.vat_number, "4123456789")
        self.assertEqual(self.landlord.landlord_type, "company")  # promoted from individual
        self.assertEqual(self.landlord.address["street"], "12 Vine Street, Stellenbosch, 7600")
        self.assertEqual(self.landlord.classification_data, classification)

    def test_happy_path_strips_markdown_fences(self):
        self.authenticate(self.agent)
        _attach_doc(self.landlord)

        classification = _full_classification()
        fenced = "```json\n" + json.dumps(classification) + "\n```"

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(fenced)
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["classification"], classification)

    def test_registration_document_is_included_in_classification(self):
        self.authenticate(self.agent)
        _attach_registration_doc(self.landlord, name="cor143_cipc.pdf")

        classification = _full_classification()
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(
                json.dumps(classification)
            )
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 200)
        # Verify the call to Claude included the registration_document block
        kwargs = client.messages.create.call_args.kwargs
        content = kwargs["messages"][0]["content"]
        labels = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        self.assertTrue(any("Registration Document" in lbl for lbl in labels))


# ─────────────────────────────────────────────────────────────────────────────
# LandlordClassifyRegistrationView — single-document endpoint
# ─────────────────────────────────────────────────────────────────────────────
@override_settings(ANTHROPIC_API_KEY="sk-fake-test")
class LandlordClassifyRegistrationViewTests(TremlyAPITestCase):
    def setUp(self):
        self.agent = self.create_agent(email="agent@classify-reg.test")
        self.landlord = self.create_landlord(
            name="",
            landlord_type="individual",
            email="",
            vat_number="",
            registration_number="",
            representative_name="",
            representative_id_number="",
            address={},
        )
        self.url = reverse("landlord-classify-registration", args=[self.landlord.pk])

    def test_missing_landlord_returns_404(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("landlord-classify-registration", args=[999999])
        )
        self.assertEqual(resp.status_code, 404)

    def test_missing_registration_document_returns_400(self):
        self.authenticate(self.agent)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No registration document", resp.data["detail"])

    @override_settings(ANTHROPIC_API_KEY="")
    def test_missing_api_key_returns_503(self):
        self.authenticate(self.agent)
        _attach_registration_doc(self.landlord)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 503)

    def test_happy_path_patches_landlord(self):
        self.authenticate(self.agent)
        _attach_registration_doc(self.landlord, name="cipc_cert.pdf")

        classification = _full_classification()
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(
                json.dumps(classification)
            )
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["document"], "cipc_cert.pdf")
        self.assertIn("registration_number", resp.data["patched_fields"])

        self.landlord.refresh_from_db()
        self.assertEqual(self.landlord.registration_number, "2021/123456/07")
        self.assertEqual(self.landlord.landlord_type, "company")

    def test_claude_invalid_json_returns_502(self):
        self.authenticate(self.agent)
        _attach_registration_doc(self.landlord)

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response("not json")
            resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, 502)
        self.assertIn("invalid JSON", resp.data["detail"])


# ─────────────────────────────────────────────────────────────────────────────
# _patch_landlord — direct unit tests on the pure helper
# ─────────────────────────────────────────────────────────────────────────────
class PatchLandlordHelperTests(TremlyAPITestCase):
    """Direct tests on the extraction → landlord field-mapping helper.

    Bypasses the API / Claude mocking entirely since the helper is pure
    Python operating on a Landlord row + a dict.
    """

    def _fresh_individual(self):
        return self.create_landlord(
            name="",
            landlord_type="individual",
            email="",
            phone="",
            vat_number="",
            registration_number="",
            representative_name="",
            representative_id_number="",
            address={},
        )

    def test_patches_all_extracted_fields(self):
        landlord = self._fresh_individual()
        patched = _patch_landlord(landlord, _full_classification())

        for field in ("name", "registration_number", "vat_number", "email",
                      "phone", "representative_name", "representative_id_number",
                      "landlord_type", "address", "classification_data"):
            assert field in patched, f"expected {field} in patched list"

        landlord.refresh_from_db()
        assert landlord.name == "Golden Wave Properties (Pty) Ltd"
        assert landlord.registration_number == "2021/123456/07"
        assert landlord.vat_number == "4123456789"
        assert landlord.phone == "0214567890"

    def test_does_not_overwrite_existing_fields(self):
        """Fields already filled by the user must be preserved."""
        landlord = self.create_landlord(
            name="User-entered Name Ltd",
            email="user@set.test",
            landlord_type="company",
            registration_number="2015/000001/07",
            vat_number="4000000000",
            address={"street": "Already set"},
        )
        patched = _patch_landlord(landlord, _full_classification())

        landlord.refresh_from_db()
        assert landlord.name == "User-entered Name Ltd"
        assert landlord.email == "user@set.test"
        assert landlord.registration_number == "2015/000001/07"
        assert landlord.vat_number == "4000000000"
        assert landlord.address == {"street": "Already set"}

        # But classification_data is ALWAYS overwritten (it's the latest snapshot)
        assert "classification_data" in patched
        assert "name" not in patched
        assert "registration_number" not in patched

    def test_entity_type_promotion_only_when_individual(self):
        """If landlord is already 'company', Claude saying 'Trust' must not
        downgrade it (avoid clobbering a manual correction)."""
        landlord = self.create_landlord(
            name="Already A Company",
            landlord_type="company",
        )
        _patch_landlord(landlord, _full_classification(entity_type="Trust"))
        landlord.refresh_from_db()
        assert landlord.landlord_type == "company", (
            "Existing landlord_type must not be downgraded by AI output"
        )

    def test_owned_by_trust_flag_is_set(self):
        landlord = self._fresh_individual()
        classification = _full_classification(owned_by_trust=True)
        patched = _patch_landlord(landlord, classification)

        landlord.refresh_from_db()
        assert landlord.owned_by_trust is True
        assert "owned_by_trust" in patched

    def test_cc_entity_type_maps_to_cc(self):
        landlord = self._fresh_individual()
        _patch_landlord(
            landlord,
            _full_classification(
                entity_type="CC",
                extracted_data={"company_name": "Mom & Pop CC", "registration_number": "CK1999/12345"},
            ),
        )
        landlord.refresh_from_db()
        assert landlord.landlord_type == "cc"

    def test_close_corporation_entity_type_maps_to_cc(self):
        """Claude sometimes uses the full 'Close Corporation' string."""
        landlord = self._fresh_individual()
        _patch_landlord(
            landlord,
            _full_classification(
                entity_type="Close Corporation",
                extracted_data={"company_name": "Mom & Pop CC"},
            ),
        )
        landlord.refresh_from_db()
        assert landlord.landlord_type == "cc"

    def test_individual_fallback_name_uses_full_name(self):
        """For individuals, Claude returns ``full_name`` instead of ``company_name``."""
        landlord = self._fresh_individual()
        _patch_landlord(
            landlord,
            _full_classification(
                entity_type="Individual",
                extracted_data={
                    "full_name": "Jane Doe",
                    "registration_number": "",
                },
            ),
        )
        landlord.refresh_from_db()
        assert landlord.name == "Jane Doe"

    def test_classification_data_always_persisted(self):
        """Even if nothing else changes, the full classification snapshot is stored."""
        landlord = self.create_landlord(name="Already Set", landlord_type="company")
        classification = _full_classification()
        _patch_landlord(landlord, classification)

        landlord.refresh_from_db()
        assert landlord.classification_data == classification

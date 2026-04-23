"""
Integration tests for the municipal-bill AI parser endpoint.

Source file under test: apps/properties/municipal_bill_view.py :: ParseMunicipalBillView

Covers:
  - Unauthenticated request → 401
  - Tenant (wrong role) → 403
  - Missing file → 400
  - Unsupported mime type → 400
  - Missing ANTHROPIC_API_KEY → 503
  - Claude APIError → 502 (with retries; message includes "Claude API failed after N attempts")
  - Claude returning no tool_use block → 502
  - Happy path with an image → 200, structured payload with image block
  - Happy path with a PDF → 200, structured payload with document block
  - Confidence scores passed through to response
  - tool_choice forced in API call

All Claude calls are mocked — no real API traffic.
"""
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


CLAUDE_CLIENT_PATH = "apps.properties.municipal_bill_view.anthropic.Anthropic"


def _fake_tool_use_response(payload: dict):
    """Build a fake anthropic SDK response with a tool_use block containing payload."""
    block = mock.MagicMock()
    block.type = "tool_use"
    block.input = payload
    resp = mock.MagicMock()
    resp.content = [block]
    return resp


def _fake_no_tool_use_response():
    """Build a fake anthropic SDK response with only a text block (no tool_use)."""
    block = mock.MagicMock()
    block.type = "text"
    block.text = "Some plain text response."
    resp = mock.MagicMock()
    resp.content = [block]
    return resp


@override_settings(ANTHROPIC_API_KEY="test-key-sk-fake")
class ParseMunicipalBillViewTests(TremlyAPITestCase):
    url = reverse("parse-municipal-bill")

    def _png_upload(self, name="bill.png", content=b"\x89PNG\r\n\x1a\nfake"):
        return SimpleUploadedFile(name, content, content_type="image/png")

    def _pdf_upload(self, name="bill.pdf", content=b"%PDF-1.4\nfake"):
        return SimpleUploadedFile(name, content, content_type="application/pdf")

    # ── Auth / permissions ─────────────────────────────────────────────────

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, {"file": self._png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, 401)

    def test_tenant_user_is_forbidden(self):
        """Only agents/admins may parse municipal bills — tenants cannot."""
        self.authenticate(self.create_tenant(email="tenant@bill.test"))
        resp = self.client.post(self.url, {"file": self._png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, 403)

    # ── Input validation ──────────────────────────────────────────────────

    def test_missing_file_returns_400(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No file provided", resp.data["detail"])

    def test_unsupported_mime_returns_400(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))
        # .docx / .txt / .csv — anything other than PDF/image is rejected
        upload = SimpleUploadedFile(
            "notes.docx",
            b"not really a docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        resp = self.client.post(self.url, {"file": upload}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Unsupported file type", resp.data["detail"])

    # ── Configuration ──────────────────────────────────────────────────────

    @override_settings(ANTHROPIC_API_KEY="")
    def test_missing_api_key_returns_503(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))
        resp = self.client.post(self.url, {"file": self._png_upload()}, format="multipart")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", resp.data["detail"])

    # ── Claude failure modes ───────────────────────────────────────────────

    def test_claude_api_error_returns_502(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))

        import anthropic
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.side_effect = anthropic.APIError(
                "server on fire",
                request=mock.MagicMock(),
                body=None,
            )
            resp = self.client.post(
                self.url, {"file": self._png_upload()}, format="multipart"
            )

        self.assertEqual(resp.status_code, 502)
        self.assertIn("Claude API failed after", resp.data["detail"])

    def test_claude_no_tool_use_block_returns_502(self):
        """When Claude returns no tool_use block (e.g. plain text), the view returns 502."""
        self.authenticate(self.create_agent(email="agent@bill.test"))

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_no_tool_use_response()
            resp = self.client.post(
                self.url, {"file": self._png_upload()}, format="multipart"
            )

        self.assertEqual(resp.status_code, 502)
        self.assertIn("no tool_use block", resp.data["detail"])

    # ── Happy paths ────────────────────────────────────────────────────────

    def test_happy_path_image_returns_extracted_json(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {
            "property_name": "18 Irene Park",
            "address": "18 Irene Park, La Colline, Stellenbosch",
            "city": "Stellenbosch",
            "province": "Western Cape",
            "postal_code": "7600",
            "total_due": 2450.37,
            "municipality": "Stellenbosch Municipality",
        }

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_tool_use_response(payload)
            resp = self.client.post(
                self.url,
                {"file": self._png_upload(name="stb_bill.png")},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["filename"], "stb_bill.png")
        self.assertEqual(resp.data["extracted"], payload)

        # Verify we actually asked Claude to process an image block
        kwargs = client.messages.create.call_args.kwargs
        content = kwargs["messages"][0]["content"]
        image_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "image"]
        self.assertEqual(len(image_blocks), 1)
        self.assertEqual(image_blocks[0]["source"]["media_type"], "image/png")

    def test_happy_path_pdf_uses_document_block(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {"property_name": "Erf 1234", "total_due": 123.45}
        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_tool_use_response(payload)
            resp = self.client.post(
                self.url,
                {"file": self._pdf_upload(name="rates.pdf")},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["extracted"], payload)

        kwargs = client.messages.create.call_args.kwargs
        content = kwargs["messages"][0]["content"]
        doc_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "document"]
        self.assertEqual(len(doc_blocks), 1)
        self.assertEqual(doc_blocks[0]["source"]["media_type"], "application/pdf")

    def test_extracted_payload_includes_confidence_scores(self):
        """View passes through confidence_scores from the tool_use result."""
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {
            "property_name": "4 Otterkuil",
            "total_due": 999.99,
            "confidence_scores": {"property_name": 95, "total_due": 90},
        }

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_tool_use_response(payload)
            resp = self.client.post(
                self.url,
                {"file": self._png_upload()},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["extracted"], payload)
        self.assertEqual(resp.data["confidence_scores"], payload["confidence_scores"])

    def test_tool_choice_is_forced_in_api_call(self):
        """View must force tool_choice so Claude always returns structured data."""
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {"property_name": "Stand 42", "total_due": 42}

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_tool_use_response(payload)
            resp = self.client.post(
                self.url,
                {"file": self._png_upload()},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        kwargs = client.messages.create.call_args.kwargs
        self.assertIn("tool_choice", kwargs)
        self.assertEqual(kwargs["tool_choice"]["type"], "tool")

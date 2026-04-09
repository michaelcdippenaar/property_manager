"""
Integration tests for the municipal-bill AI parser endpoint.

Source file under test: apps/properties/municipal_bill_view.py :: ParseMunicipalBillView

Covers:
  - Unauthenticated request → 401
  - Tenant (wrong role) → 403
  - Missing file → 400
  - Unsupported mime type → 400
  - Missing ANTHROPIC_API_KEY → 503
  - Claude APIError → 502
  - Claude returning invalid JSON → 502 with ``raw`` preview
  - Claude returning JSON wrapped in ```json fences → parsed successfully
  - Happy path with an image → 200, structured payload

All Claude calls are mocked — no real API traffic.
"""
import json
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


CLAUDE_CLIENT_PATH = "apps.properties.municipal_bill_view.anthropic.Anthropic"


def _fake_claude_response(text: str):
    """Build a fake anthropic SDK response whose content[0].text == text."""
    block = mock.MagicMock()
    block.text = text
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
        self.assertIn("Claude API error", resp.data["detail"])

    def test_claude_invalid_json_returns_502_with_raw_preview(self):
        self.authenticate(self.create_agent(email="agent@bill.test"))

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(
                "definitely-not-json { broken"
            )
            resp = self.client.post(
                self.url, {"file": self._png_upload()}, format="multipart"
            )

        self.assertEqual(resp.status_code, 502)
        self.assertIn("invalid JSON", resp.data["detail"])
        self.assertIn("raw", resp.data)
        # Preview is capped at 500 chars
        self.assertLessEqual(len(resp.data["raw"]), 500)

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
            client.messages.create.return_value = _fake_claude_response(json.dumps(payload))
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
            client.messages.create.return_value = _fake_claude_response(json.dumps(payload))
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

    def test_markdown_fenced_json_is_parsed(self):
        """Claude sometimes wraps JSON in ```json … ``` despite the system prompt."""
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {"property_name": "4 Otterkuil", "total_due": 999.99}
        fenced = "```json\n" + json.dumps(payload) + "\n```"

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(fenced)
            resp = self.client.post(
                self.url,
                {"file": self._png_upload()},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["extracted"], payload)

    def test_plain_fenced_json_without_language_tag_is_parsed(self):
        """```\n{...}\n``` (no 'json' after the opening fence) must also work."""
        self.authenticate(self.create_agent(email="agent@bill.test"))

        payload = {"property_name": "Stand 42", "total_due": 42}
        fenced = "```\n" + json.dumps(payload) + "\n```"

        with mock.patch(CLAUDE_CLIENT_PATH) as client_cls:
            client = client_cls.return_value
            client.messages.create.return_value = _fake_claude_response(fenced)
            resp = self.client.post(
                self.url,
                {"file": self._png_upload()},
                format="multipart",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["extracted"], payload)

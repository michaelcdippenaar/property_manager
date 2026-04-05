"""Tests for LeaseTemplate views: list, create, detail, preview, AI chat, export PDF."""
import pytest
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.leases.models import LeaseTemplate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class LeaseTemplateTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.template = LeaseTemplate.objects.create(
            name="Standard Lease",
            version="1.0",
            province="Western Cape",
            docx_file=SimpleUploadedFile("template.docx", b"PK\x03\x04"),
            content_html='<p>Lease for <span data-merge-field="tenant_name">__</span></p>',
        )

    def test_list_templates(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-templates"))
        self.assertEqual(resp.status_code, 200)

    def test_create_template(self):
        self.authenticate(self.agent)
        f = SimpleUploadedFile("new.docx", b"PK\x03\x04", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        resp = self.client.post(
            reverse("lease-templates"),
            {"name": "New Template", "version": "2.0", "docx_file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

    def test_get_template_detail(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-template-detail", args=[self.template.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("detected_variables", resp.data)

    def test_update_template(self):
        self.authenticate(self.agent)
        resp = self.client.patch(
            reverse("lease-template-detail", args=[self.template.pk]),
            {"name": "Updated Template"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Updated Template")

    def test_preview_template_invalid_docx(self):
        """
        BUG: Preview endpoint doesn't catch docx.opc.exceptions.PackageNotFoundError
        when the file exists on disk but isn't a valid docx package.
        """
        self.authenticate(self.agent)
        # The stub docx file bytes are invalid, so python-docx raises an error
        # that the view doesn't handle, causing 500.
        from docx.opc.exceptions import PackageNotFoundError
        with self.assertRaises(PackageNotFoundError):
            self.client.get(reverse("lease-template-preview", args=[self.template.pk]))

    @mock.patch("anthropic.Anthropic")
    @mock.patch("apps.leases.template_views._get_anthropic_api_key", return_value="test-key")
    def test_ai_chat_mocked(self, mock_key, mock_anthropic_cls):
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.content = [mock.MagicMock(text="Here is the AI reply.")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-template-ai-chat", args=[self.template.pk]),
            {"message": "Add a pet clause"},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])

    @mock.patch("apps.leases.template_views._get_anthropic_api_key", return_value="")
    def test_ai_chat_no_api_key(self, mock_key):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-template-ai-chat", args=[self.template.pk]),
            {"message": "Add clause"},
            format="json",
        )
        self.assertIn(resp.status_code, [400, 500, 503])

    def test_unauthenticated(self):
        resp = self.client.get(reverse("lease-templates"))
        self.assertEqual(resp.status_code, 401)

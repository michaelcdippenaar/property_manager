"""Tests for tenant AI conversations: list, create, detail, messages, maintenance draft."""
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from apps.ai.models import TenantChatSession
from tests.base import TremlyAPITestCase


MOCK_AI_RESPONSE_JSON = '{"reply": "I can help with that.", "conversation_title": null, "maintenance_ticket": null}'
MOCK_AI_RESPONSE_TICKET = (
    '{"reply": "I have noted the leak.", "conversation_title": "Kitchen leak",'
    ' "maintenance_ticket": {"title": "Kitchen tap leaking", "description": "Tap drips constantly", "priority": "medium"}}'
)


def _stored_msg(mid: int, role: str, content: str) -> dict:
    return {
        "id": mid,
        "role": role,
        "content": content,
        "created_at": timezone.now().isoformat(),
        "attachment_kind": "",
    }


class ConversationListCreateTests(TremlyAPITestCase):

    def setUp(self):
        self.tenant = self.create_tenant()
        self.other_tenant = self.create_tenant(email="other_tenant@test.com")
        self.conv = TenantChatSession.objects.create(
            user=self.tenant, title="Test Conv", messages=[],
        )
        TenantChatSession.objects.create(
            user=self.other_tenant, title="Other Conv", messages=[],
        )

    def test_list_own_only(self):
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("tenant-ai-conversations"))
        self.assertEqual(resp.status_code, 200)
        titles = [c["title"] for c in resp.data]
        self.assertIn("Test Conv", titles)
        self.assertNotIn("Other Conv", titles)

    def test_create(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-conversations"),
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["title"], "New conversation")

    def test_create_custom_title(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-conversations"),
            {"title": "My Issue"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["title"], "My Issue")

    def test_unauthenticated(self):
        resp = self.client.get(reverse("tenant-ai-conversations"))
        self.assertEqual(resp.status_code, 401)


class ConversationDetailTests(TremlyAPITestCase):

    def setUp(self):
        self.tenant = self.create_tenant()
        self.conv = TenantChatSession.objects.create(
            user=self.tenant,
            title="Detail Conv",
            messages=[_stored_msg(1, "user", "Hello")],
        )

    def test_get_detail(self):
        self.authenticate(self.tenant)
        resp = self.client.get(
            reverse("tenant-ai-conversation-detail", args=[self.conv.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Detail Conv")
        self.assertGreaterEqual(len(resp.data["messages"]), 1)
        self.assertIn("maintenance_request_id", resp.data)
        self.assertIn("agent_question_id", resp.data)

    def test_other_users_404(self):
        other = self.create_tenant(email="other@test.com")
        self.authenticate(other)
        resp = self.client.get(
            reverse("tenant-ai-conversation-detail", args=[self.conv.pk])
        )
        self.assertEqual(resp.status_code, 404)


class ConversationMessageTests(TremlyAPITestCase):

    def setUp(self):
        self.tenant = self.create_tenant()
        self.conv = TenantChatSession.objects.create(
            user=self.tenant, title="Msg Conv", messages=[],
        )

    def _mock_anthropic(self, response_text=MOCK_AI_RESPONSE_JSON):
        """Return a context manager that mocks Anthropic + RAG."""
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.content = [mock.MagicMock(text=response_text)]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        return mock.patch.multiple(
            "apps.tenant_portal.views",
            _get_anthropic_api_key=mock.MagicMock(return_value="test-key"),
            query_contracts=mock.MagicMock(return_value="relevant text"),
            anthropic=mock.MagicMock(**{"Anthropic.return_value": mock_client}),
            extract_anthropic_assistant_text=mock.MagicMock(return_value=response_text),
            build_web_fetch_tools=mock.MagicMock(return_value=[]),
        )

    def test_send_message_success(self):
        self.authenticate(self.tenant)
        with self._mock_anthropic():
            resp = self.client.post(
                reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
                {"content": "My tap is leaking"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ai_message", resp.data)
        self.assertIn("user_message", resp.data)

    def test_send_message_empty(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
            {"content": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.tenant_portal.views._get_anthropic_api_key", return_value="")
    @mock.patch("apps.tenant_portal.views.query_contracts", return_value="")
    def test_no_api_key(self, mock_rag, mock_key):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
            {"content": "hello"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("not available", resp.data["ai_message"]["content"])

    def test_ai_error_returns_502(self):
        self.authenticate(self.tenant)
        with mock.patch.multiple(
            "apps.tenant_portal.views",
            _get_anthropic_api_key=mock.MagicMock(return_value="test-key"),
            query_contracts=mock.MagicMock(return_value=""),
            build_web_fetch_tools=mock.MagicMock(return_value=[]),
            anthropic=mock.MagicMock(**{
                "Anthropic.return_value.messages.create.side_effect": Exception("API Error")
            }),
        ):
            resp = self.client.post(
                reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
                {"content": "help"},
                format="json",
            )
        self.assertEqual(resp.status_code, 502)

    def test_maintenance_ticket_created(self):
        # Need an active lease for the tenant so _default_unit_for_user returns a unit
        person = self.create_person(full_name="Tenant P", linked_user=self.tenant)
        prop = self.create_property()
        unit = self.create_unit(property_obj=prop)
        self.create_lease(unit=unit, primary_tenant=person)

        self.authenticate(self.tenant)
        with self._mock_anthropic(MOCK_AI_RESPONSE_TICKET):
            resp = self.client.post(
                reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
                {"content": "My kitchen tap is leaking badly"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data.get("maintenance_request"))
        self.assertTrue(resp.data.get("maintenance_report_suggested"))
        self.assertIsNotNone(resp.data.get("maintenance_request_id"))

    def test_other_users_convo_404(self):
        other = self.create_tenant(email="other@test.com")
        self.authenticate(other)
        resp = self.client.post(
            reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
            {"content": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_file_upload_unsupported_type(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.authenticate(self.tenant)
        f = SimpleUploadedFile("doc.txt", b"text", content_type="text/plain")
        resp = self.client.post(
            reverse("tenant-ai-conversation-messages", args=[self.conv.pk]),
            {"content": "see attached", "file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)


class MaintenanceDraftTests(TremlyAPITestCase):

    def setUp(self):
        self.tenant = self.create_tenant()
        self.conv = TenantChatSession.objects.create(
            user=self.tenant,
            title="Draft Conv",
            maintenance_report_suggested=True,
            messages=[
                _stored_msg(1, "user", "My tap is broken"),
                _stored_msg(2, "assistant", "I can help."),
            ],
        )

    @mock.patch("apps.tenant_portal.views.anthropic.Anthropic")
    @mock.patch("apps.tenant_portal.views._get_anthropic_api_key", return_value="test-key")
    @mock.patch("apps.tenant_portal.views.extract_anthropic_assistant_text")
    @mock.patch("apps.tenant_portal.views.parse_maintenance_draft_response")
    def test_draft_success(self, mock_parse, mock_extract, mock_key, mock_cls):
        mock_extract.return_value = '{"title": "Broken tap", "description": "Tap drips"}'
        mock_parse.return_value = {"title": "Broken tap", "description": "Tap drips", "priority": "medium"}
        mock_client = mock.MagicMock()
        mock_cls.return_value = mock_client

        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-maintenance-draft", args=[self.conv.pk]),
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("title", resp.data)

    def test_no_maintenance_context(self):
        conv2 = TenantChatSession.objects.create(
            user=self.tenant,
            title="No Maint",
            maintenance_report_suggested=False,
            messages=[],
        )
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-maintenance-draft", args=[conv2.pk]),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.tenant_portal.views.anthropic.Anthropic")
    @mock.patch("apps.tenant_portal.views._get_anthropic_api_key", return_value="test-key")
    def test_ai_error(self, mock_key, mock_cls):
        mock_client = mock.MagicMock()
        mock_client.messages.create.side_effect = Exception("API down")
        mock_cls.return_value = mock_client

        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("tenant-ai-maintenance-draft", args=[self.conv.pk]),
            format="json",
        )
        self.assertEqual(resp.status_code, 502)

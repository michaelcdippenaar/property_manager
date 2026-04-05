"""Tests for ReusableClause CRUD, generate, extract."""
import pytest
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.leases.models import LeaseTemplate, ReusableClause
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class ReusableClauseTests(TremlyAPITestCase):

    def setUp(self):
        self.agent1 = self.create_agent(email="agent1@test.com")
        self.agent2 = self.create_agent(email="agent2@test.com")
        self.clause1 = ReusableClause.objects.create(
            title="Deposit Clause",
            category="financial",
            html="<p>Deposit terms</p>",
            created_by=self.agent1,
        )
        self.clause2 = ReusableClause.objects.create(
            title="Pet Clause",
            category="general",
            html="<p>No pets allowed</p>",
            created_by=self.agent2,
        )

    def test_list_clauses_own_only(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("clauses-list"))
        self.assertEqual(resp.status_code, 200)
        titles = [c["title"] for c in resp.data["results"]]
        self.assertIn("Deposit Clause", titles)
        self.assertNotIn("Pet Clause", titles)

    def test_list_clauses_filter_category(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("clauses-list"), {"category": "financial"})
        self.assertEqual(resp.status_code, 200)
        for c in resp.data["results"]:
            self.assertEqual(c["category"], "financial")

    def test_list_clauses_search(self):
        self.authenticate(self.agent1)
        resp = self.client.get(reverse("clauses-list"), {"q": "Deposit"})
        self.assertEqual(resp.status_code, 200)

    def test_create_clause(self):
        self.authenticate(self.agent1)
        resp = self.client.post(reverse("clauses-list"), {
            "title": "New Clause",
            "category": "legal",
            "html": "<p>Legal terms</p>",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(ReusableClause.objects.filter(title="New Clause", created_by=self.agent1).exists())

    def test_delete_clause(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("clause-destroy", args=[self.clause1.pk]))
        self.assertEqual(resp.status_code, 204)

    def test_delete_other_users_clause(self):
        self.authenticate(self.agent1)
        resp = self.client.delete(reverse("clause-destroy", args=[self.clause2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_use_clause_increments_count(self):
        self.authenticate(self.agent1)
        initial_count = self.clause1.use_count
        resp = self.client.post(reverse("clause-use", args=[self.clause1.pk]))
        self.assertEqual(resp.status_code, 200)
        self.clause1.refresh_from_db()
        self.assertEqual(self.clause1.use_count, initial_count + 1)


class GenerateClauseTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()

    @mock.patch("anthropic.Anthropic")
    @mock.patch("apps.leases.clause_views._get_anthropic_api_key", return_value="test-key")
    def test_generate_clause(self, mock_key, mock_cls):
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.content = [mock.MagicMock(text='{"options":[{"title":"Pet Clause","html":"<p>Pets allowed</p>","category":"general"}]}')]
        mock_client.messages.create.return_value = mock_response
        mock_cls.return_value = mock_client

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("clauses-generate"),
            {"topic": "pets policy"},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_generate_clause_no_topic(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("clauses-generate"), {"topic": ""}, format="json")
        self.assertEqual(resp.status_code, 400)


class ExtractClausesTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.template = LeaseTemplate.objects.create(
            name="Extract T",
            docx_file=SimpleUploadedFile("t.docx", b"PK"),
            content_html="<p>Some clause content here</p>",
        )

    @mock.patch("anthropic.Anthropic")
    @mock.patch("apps.leases.clause_views._get_anthropic_api_key", return_value="test-key")
    def test_extract_clauses(self, mock_key, mock_cls):
        mock_client = mock.MagicMock()
        mock_response = mock.MagicMock()
        mock_response.content = [mock.MagicMock(text='{"clauses":[{"title":"Clause 1","html":"<p>C1</p>","category":"general"}]}')]
        mock_client.messages.create.return_value = mock_response
        mock_cls.return_value = mock_client

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("clauses-extract"),
            {"template_id": self.template.pk},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_extract_no_template_id(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("clauses-extract"), {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_extract_template_not_found(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("clauses-extract"),
            {"template_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

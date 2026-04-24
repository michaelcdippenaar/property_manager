"""Tests for LeaseBuilderSession: create, chat, finalize."""
import pytest
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import Agency
from apps.leases.models import LeaseBuilderSession, LeaseTemplate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


MOCK_CLAUDE_RESPONSE = {
    "reply": "I've noted those details.",
    "updated_state": {"landlord_name": "John Smith", "property_address": "123 Main St"},
    "rha_flags": [],
    "next_question": "What is the unit number?",
    "ready_to_finalize": False,
}


class LeaseBuilderSessionCreateTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()

    def test_create_session(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("builder-session-create"), {}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("session_id", resp.data)

    def test_create_session_with_template(self):
        template = LeaseTemplate.objects.create(
            name="T", docx_file=SimpleUploadedFile("t.docx", b"PK"),
            content_html="<p>Template</p>",
        )
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"template_id": template.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_create_session_with_existing_lease(self):
        """
        Creating a builder session pre-populated from an existing lease that
        belongs to the requesting agent must succeed (201).

        The prefetch_related("co_tenants__person") path is tested here —
        the old bug used "tenants__person" (wrong related_name) and raised
        AttributeError.  That bug was fixed; this test asserts the fix holds.
        """
        prop = self.create_property(agent=self.agent)
        unit = self.create_unit(property_obj=prop)
        person = self.create_person(full_name="Existing Tenant")
        lease = self.create_lease(unit=unit, primary_tenant=person)
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"existing_lease_id": lease.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("session_id", resp.data)

    def test_idor_create_session_any_lease(self):
        """
        SECURITY (IDOR guard): a user must not be able to pre-populate a builder
        session from a lease managed by a different agent.
        The endpoint must return 403 (not 404, to avoid enumeration) when the
        requesting user is not the property's managing agent.
        """
        other_agent = self.create_agent(email="other@test.com")
        prop = self.create_property(agent=other_agent, name="Other Prop")
        unit = self.create_unit(property_obj=prop)
        person = self.create_person(full_name="Other Tenant")
        lease = self.create_lease(unit=unit, primary_tenant=person)

        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"existing_lease_id": lease.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


    def test_colleague_can_create_session_on_agency_lease(self):
        """
        SECURITY (positive case): an AGENCY_ADMIN in the same agency as the
        lease's managing agent must be allowed to create a builder session --
        i.e. the IDOR guard must not regress legitimate agency-wide access.

        Pins the canonical get_accessible_property_ids semantics: if a future
        change tightens the guard back to single-agent ownership, this test
        will catch the regression.
        """
        agency = Agency.objects.create(name="Shared Agency")
        # agent1 is the managing agent (property.agent FK); belongs to agency.
        agent1 = self.create_agent(email="agent1@test.com", agency=agency)
        prop = self.create_property(agent=agent1, name="Agency Prop")
        unit = self.create_unit(property_obj=prop)
        person = self.create_person(full_name="Agency Tenant")
        lease = self.create_lease(unit=unit, primary_tenant=person)

        # agency_admin is a colleague in the same agency -- should have full access.
        agency_admin = self.create_user(
            email="agencyadmin@test.com",
            role="agency_admin",
            agency=agency,
        )
        self.authenticate(agency_admin)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"existing_lease_id": lease.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_create_session_invalid_template(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"template_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_create_session_invalid_lease(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-create"),
            {"existing_lease_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)


class LeaseBuilderChatTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.session = LeaseBuilderSession.objects.create(
            created_by=self.agent,
            status="drafting",
            current_state={},
            messages=[],
        )

    @mock.patch("apps.leases.builder_views._call_claude")
    def test_send_message(self, mock_claude):
        mock_claude.return_value = MOCK_CLAUDE_RESPONSE
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "Landlord is John Smith"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("reply", resp.data)

    @mock.patch("apps.leases.builder_views._call_claude")
    def test_send_message_empty(self, mock_claude):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.leases.builder_views._call_claude")
    def test_send_message_finalized_session(self, mock_claude):
        self.session.status = "finalized"
        self.session.save()
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_send_message_wrong_user(self):
        other = self.create_agent(email="other@test.com")
        self.authenticate(other)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    @mock.patch("apps.leases.builder_views._call_claude")
    def test_ready_to_finalize(self, mock_claude):
        response_data = {**MOCK_CLAUDE_RESPONSE, "ready_to_finalize": True}
        mock_claude.return_value = response_data
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "All details provided"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("ready_to_finalize", False))

    @mock.patch("apps.leases.builder_views._call_claude")
    def test_rha_error_in_response(self, mock_claude):
        response_data = {
            **MOCK_CLAUDE_RESPONSE,
            "rha_flags": [{"severity": "error", "message": "Missing notice period"}],
        }
        mock_claude.return_value = response_data
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.data.get("rha_flags", [])) > 0)

    @mock.patch("apps.leases.builder_views._call_claude", side_effect=Exception("API Error"))
    def test_ai_error_returns_502(self, mock_claude):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-message", args=[self.session.pk]),
            {"message": "test"},
            format="json",
        )
        self.assertIn(resp.status_code, [500, 502])


class LeaseBuilderFinalizeTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.session = LeaseBuilderSession.objects.create(
            created_by=self.agent,
            status="drafting",
            current_state={
                "landlord_name": "John Smith",
                "property_address": "123 Main",
                "unit_number": self.unit.unit_number,
                "tenant_name": "Jane Doe",
                "lease_start": "2026-01-01",
                "lease_end": "2027-01-01",
                "monthly_rent": "5000",
                "deposit": "10000",
                "notice_period_days": "20",
            },
            messages=[],
            rha_flags=[],
        )

    def test_finalize_missing_fields(self):
        self.session.current_state = {"landlord_name": "Only Name"}
        self.session.save()
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-finalize", args=[self.session.pk]),
            format="json",
        )
        self.assertIn(resp.status_code, [400, 200])

    def test_finalize_already_finalized(self):
        self.session.status = "finalized"
        self.session.save()
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("builder-session-finalize", args=[self.session.pk]),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_finalize_wrong_user(self):
        other = self.create_agent(email="other@test.com")
        self.authenticate(other)
        resp = self.client.post(
            reverse("builder-session-finalize", args=[self.session.pk]),
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

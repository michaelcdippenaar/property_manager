"""Tests for MaintenanceRequestViewSet, activity, dispatch, skills, agent questions."""
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from apps.maintenance.models import (
    AgentQuestion, JobDispatch, JobQuoteRequest, MaintenanceActivity,
    MaintenanceRequest, MaintenanceSkill, Supplier, SupplierTrade,
)
from tests.base import TremlyAPITestCase


class MaintenanceRequestViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit, tenant=self.tenant)

    def test_tenant_sees_own_requests(self):
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("maintenance-list"))
        self.assertEqual(resp.status_code, 200)
        for item in resp.data["results"]:
            self.assertEqual(item["tenant"], self.tenant.pk)

    def test_agent_sees_all_requests(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_create_maintenance_request(self):
        self.authenticate(self.tenant)
        resp = self.client.post(reverse("maintenance-list"), {
            "unit": self.unit.pk,
            "title": "Broken window",
            "description": "Window is cracked",
            "priority": "high",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["tenant"], self.tenant.pk)

    def test_create_maintenance_request_with_initial_chat_history(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("maintenance-list"),
            {
                "unit": self.unit.pk,
                "title": "Broken window",
                "description": "Window is cracked",
                "priority": "high",
                "initial_chat_history": [
                    {"role": "user", "content": "The window cracked during the storm."},
                    {"role": "assistant", "content": "I can log that for maintenance."},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        acts = list(MaintenanceActivity.objects.filter(request_id=resp.data["id"]).order_by("created_at"))
        self.assertEqual(len(acts), 2)
        self.assertEqual(acts[0].message, "The window cracked during the storm.")
        self.assertEqual(acts[0].metadata["chat_source"], "maintenance_create_api")
        self.assertEqual(acts[1].metadata["source"], "ai_agent")

    def test_filter_by_status(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-list"), {"status": "open"})
        for item in resp.data["results"]:
            self.assertEqual(item["status"], "open")

    def test_filter_by_priority(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-list"), {"priority": "medium"})
        for item in resp.data["results"]:
            self.assertEqual(item["priority"], "medium")

    def test_exclude_status(self):
        closed_mr = self.create_maintenance_request(
            unit=self.unit, tenant=self.tenant, status="closed",
            title="Closed issue",
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-list"), {"exclude_status": "closed"})
        ids = [item["id"] for item in resp.data["results"]]
        self.assertNotIn(closed_mr.pk, ids)

    def test_update_status(self):
        self.authenticate(self.agent)
        resp = self.client.patch(
            reverse("maintenance-detail", args=[self.mr.pk]),
            {"status": "resolved"},
        )
        self.assertEqual(resp.status_code, 200)
        self.mr.refresh_from_db()
        self.assertEqual(self.mr.status, "resolved")

    def test_unauthenticated(self):
        resp = self.client.get(reverse("maintenance-list"))
        self.assertEqual(resp.status_code, 401)


class MaintenanceActivityTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit)

    def test_list_activity(self):
        MaintenanceActivity.objects.create(
            request=self.mr, activity_type="note", message="Test note",
            created_by=self.agent,
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-activity", args=[self.mr.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_create_activity(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-activity", args=[self.mr.pk]),
            {"activity_type": "note", "message": "Contacted supplier"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["created_by"], self.agent.pk)
        self.assertEqual(resp.data["metadata"], {})


class MaintenanceDispatchTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit)
        self.supplier = self.create_supplier()
        SupplierTrade.objects.create(supplier=self.supplier, trade="plumbing")

    @mock.patch("apps.maintenance.views.rank_suppliers", return_value=[])
    def test_create_dispatch(self, mock_rank):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("maintenance-job-dispatch", args=[self.mr.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("dispatch", resp.data)

    def test_get_dispatch_not_exists(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("maintenance-job-dispatch", args=[self.mr.pk]))
        self.assertEqual(resp.status_code, 404)

    @mock.patch("apps.maintenance.views.notify_supplier")
    def test_dispatch_send(self, mock_notify):
        jd = JobDispatch.objects.create(maintenance_request=self.mr, dispatched_by=self.agent)
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-dispatch-send", args=[self.mr.pk]),
            {"supplier_ids": [self.supplier.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["sent"], 1)
        mock_notify.assert_called()

    def test_dispatch_send_no_suppliers(self):
        JobDispatch.objects.create(maintenance_request=self.mr, dispatched_by=self.agent)
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-dispatch-send", args=[self.mr.pk]),
            {"supplier_ids": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.maintenance.views.notify_supplier")
    def test_dispatch_award(self, mock_notify):
        jd = JobDispatch.objects.create(
            maintenance_request=self.mr, dispatched_by=self.agent, status="sent",
        )
        qr = JobQuoteRequest.objects.create(
            dispatch=jd, supplier=self.supplier, status="quoted",
        )
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": qr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        qr.refresh_from_db()
        self.assertEqual(qr.status, "awarded")
        self.mr.refresh_from_db()
        self.assertEqual(self.mr.status, "in_progress")


class MaintenanceSkillViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()

    def test_list_skills(self):
        MaintenanceSkill.objects.create(name="Fix Leak", trade="plumbing")
        self.authenticate(self.agent)
        resp = self.client.get(reverse("skill-list"))
        self.assertEqual(resp.status_code, 200)

    def test_create_skill(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("skill-list"), {
            "name": "Replace Geyser",
            "trade": "plumbing",
            "difficulty": "hard",
        })
        self.assertEqual(resp.status_code, 201)


class AgentQuestionViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.question = AgentQuestion.objects.create(
            question="What is the gate code?",
            category="property",
        )

    def test_answer_question(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("agent-question-answer", args=[self.question.pk]),
            {"answer": "Gate code is 1234"},
        )
        self.assertEqual(resp.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.status, "answered")
        self.assertEqual(self.question.answered_by, self.agent)

    def test_answer_empty(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("agent-question-answer", args=[self.question.pk]),
            {"answer": ""},
        )
        self.assertEqual(resp.status_code, 400)

    def test_dismiss_question(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("agent-question-dismiss", args=[self.question.pk]),
        )
        self.assertEqual(resp.status_code, 200)
        self.question.refresh_from_db()
        self.assertEqual(self.question.status, "dismissed")

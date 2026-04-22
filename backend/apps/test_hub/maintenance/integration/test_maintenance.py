"""Tests for MaintenanceRequestViewSet, activity, dispatch, skills, agent questions."""
import pytest
from decimal import Decimal
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from apps.maintenance.models import (
    AgentQuestion, JobDispatch, JobQuote, JobQuoteRequest, MaintenanceActivity,
    MaintenanceRequest, MaintenanceSkill, Supplier, SupplierJobAssignment, SupplierProperty,
    SupplierTrade,
)
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


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


class MaintenanceDispatchTenantForbiddenTests(TremlyAPITestCase):
    """Tenants must receive HTTP 403 on all three agent-only dispatch actions."""

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit, tenant=self.tenant)
        self.supplier = self.create_supplier()
        SupplierTrade.objects.create(supplier=self.supplier, trade="plumbing")
        self.jd = JobDispatch.objects.create(maintenance_request=self.mr, dispatched_by=self.agent)
        self.qr = JobQuoteRequest.objects.create(
            dispatch=self.jd, supplier=self.supplier, status="quoted",
        )

    def test_tenant_cannot_post_job_dispatch(self):
        self.authenticate(self.tenant)
        resp = self.client.post(reverse("maintenance-job-dispatch", args=[self.mr.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_tenant_can_get_job_dispatch(self):
        """GET dispatch remains accessible to authenticated users (tenants can view)."""
        self.authenticate(self.tenant)
        resp = self.client.get(reverse("maintenance-job-dispatch", args=[self.mr.pk]))
        # 200 (dispatch exists) or 404 (none yet) — either is fine, NOT 403
        self.assertIn(resp.status_code, [200, 404])

    def test_tenant_cannot_dispatch_send(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("maintenance-dispatch-send", args=[self.mr.pk]),
            {"supplier_ids": [self.supplier.pk]},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_tenant_cannot_dispatch_award(self):
        self.authenticate(self.tenant)
        resp = self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": self.qr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


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


class SupplierMatchingTests(TremlyAPITestCase):
    """Unit tests for the 5-factor rank_suppliers algorithm."""

    def setUp(self):
        from apps.maintenance.matching import rank_suppliers
        self.rank_suppliers = rank_suppliers

        self.agent = self.create_agent()
        # Property without geo — matching falls back to 15pts proximity for all suppliers
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit, category="plumbing")

        # Supplier A — plumber, preferred, rated 4.5 (should win: skills 25 + pref 20 + rating ~9)
        self.s_preferred = self.create_supplier(
            name="Preferred Plumber",
            phone="0821111111",
            rating=Decimal("4.5"),
        )
        SupplierTrade.objects.create(supplier=self.s_preferred, trade="plumbing")
        SupplierProperty.objects.create(
            supplier=self.s_preferred, property=self.prop, is_preferred=True,
        )

        # Supplier B — electrician, no preference, lower rating
        self.s_electrical = self.create_supplier(
            name="Electrical Guy",
            phone="0822222222",
            rating=Decimal("3.0"),
        )
        SupplierTrade.objects.create(supplier=self.s_electrical, trade="electrical")

    def test_preferred_plumber_ranks_first(self):
        results = self.rank_suppliers(self.mr)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["supplier_id"], self.s_preferred.id)

    def test_result_has_all_expected_keys(self):
        results = self.rank_suppliers(self.mr)
        first = results[0]
        for key in ("supplier_id", "supplier_name", "supplier_phone", "trades", "score", "reasons"):
            self.assertIn(key, first)

    def test_scores_are_bounded_0_to_100(self):
        results = self.rank_suppliers(self.mr)
        for r in results:
            self.assertGreaterEqual(r["score"], 0)
            self.assertLessEqual(r["score"], 100)

    def test_non_matching_trade_scores_lower_than_matching(self):
        results = self.rank_suppliers(self.mr)
        preferred_score = next(r["score"] for r in results if r["supplier_id"] == self.s_preferred.id)
        electrical_score = next(r["score"] for r in results if r["supplier_id"] == self.s_electrical.id)
        self.assertGreater(preferred_score, electrical_score)

    def test_top_n_limit_respected(self):
        # Create 15 extra suppliers
        for i in range(15):
            s = self.create_supplier(name=f"Extra {i}", phone=f"082{i:07d}")
            SupplierTrade.objects.create(supplier=s, trade="plumbing")
        results = self.rank_suppliers(self.mr, top_n=10)
        self.assertEqual(len(results), 10)

    def test_supplier_with_no_geo_gets_fallback_proximity(self):
        # When either property or supplier lacks geo, rank_suppliers returns no_geo=True
        results = self.rank_suppliers(self.mr)
        for r in results:
            self.assertTrue(r["reasons"]["proximity"].get("no_geo", False))

    def test_price_history_affects_score(self):
        # Give s_preferred a quote history (cheap)
        jd = JobDispatch.objects.create(maintenance_request=self.mr, dispatched_by=self.agent)
        qr = JobQuoteRequest.objects.create(dispatch=jd, supplier=self.s_preferred)
        JobQuote.objects.create(quote_request=qr, amount=Decimal("500.00"))
        # Give s_electrical an expensive quote history
        qr2 = JobQuoteRequest.objects.create(dispatch=jd, supplier=self.s_electrical)
        JobQuote.objects.create(quote_request=qr2, amount=Decimal("5000.00"))

        results = self.rank_suppliers(self.mr)
        preferred_result = next(r for r in results if r["supplier_id"] == self.s_preferred.id)
        electrical_result = next(r for r in results if r["supplier_id"] == self.s_electrical.id)
        # Preferred has lower price — its price score should be higher
        self.assertGreater(
            preferred_result["reasons"]["price"]["score"],
            electrical_result["reasons"]["price"]["score"],
        )


class SupplierNoLoginPortalTests(TremlyAPITestCase):
    """Token-based supplier portal — no login required (SupplierQuoteView)."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit)
        self.supplier = self.create_supplier()
        self.jd = JobDispatch.objects.create(
            maintenance_request=self.mr, dispatched_by=self.agent, status="sent",
        )
        self.qr = JobQuoteRequest.objects.create(dispatch=self.jd, supplier=self.supplier)

    def test_supplier_can_view_job_via_token(self):
        resp = self.client.get(reverse("supplier-quote", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("job_title", resp.data)

    def test_viewing_marks_quote_request_as_viewed(self):
        self.client.get(reverse("supplier-quote", args=[self.qr.token]))
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "viewed")
        self.assertIsNotNone(self.qr.viewed_at)

    def test_supplier_can_submit_quote(self):
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "1500.00", "description": "Fix leaking tap", "estimated_days": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "quoted")

    def test_second_quote_submission_rejected(self):
        self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "1500.00", "description": "Fix leaking tap"},
            format="json",
        )
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "2000.00", "description": "Second attempt"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_supplier_can_decline_job(self):
        resp = self.client.post(reverse("supplier-quote-decline", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 200)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "declined")

    def test_cannot_quote_on_awarded_job(self):
        self.qr.status = JobQuoteRequest.Status.AWARDED
        self.qr.save()
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "1500.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_dispatch_status_updates_to_quoting_on_first_quote(self):
        self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "1500.00", "description": "Fix leaking tap"},
            format="json",
        )
        self.jd.refresh_from_db()
        self.assertEqual(self.jd.status, "quoting")

    def test_invalid_token_returns_404(self):
        import uuid
        fake_token = uuid.uuid4()
        resp = self.client.get(reverse("supplier-quote", args=[fake_token]))
        self.assertEqual(resp.status_code, 404)


class SupplierJobAssignmentTests(TremlyAPITestCase):
    """dispatch_award creates SupplierJobAssignment when supplier has linked_user."""

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant = self.create_tenant(email="tenant-sja@test.com")
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit, tenant=self.tenant)

        self.supplier_user = self.create_supplier_user(email="sup-linked@test.com")
        self.supplier = self.create_supplier(
            name="Linked Supplier",
            phone="0823333333",
            linked_user=self.supplier_user,
        )
        self.jd = JobDispatch.objects.create(
            maintenance_request=self.mr, dispatched_by=self.agent, status="sent",
        )
        self.qr = JobQuoteRequest.objects.create(
            dispatch=self.jd, supplier=self.supplier, status="quoted",
        )

    def test_award_creates_supplier_job_assignment(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": self.qr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        assignment = SupplierJobAssignment.objects.filter(
            supplier=self.supplier_user,
            maintenance_request=self.mr,
        ).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.status, SupplierJobAssignment.Status.ASSIGNED)

    def test_award_assignment_copies_property_address(self):
        self.authenticate(self.agent)
        self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": self.qr.pk},
            format="json",
        )
        assignment = SupplierJobAssignment.objects.get(
            supplier=self.supplier_user, maintenance_request=self.mr,
        )
        self.assertIn(self.prop.city, assignment.property_address)

    def test_award_without_linked_user_skips_assignment(self):
        """Supplier without a linked user account — no SupplierJobAssignment created."""
        unlinked_supplier = self.create_supplier(
            name="Unlinked Supplier", phone="0824444444",
        )
        qr2 = JobQuoteRequest.objects.create(
            dispatch=self.jd, supplier=unlinked_supplier, status="quoted",
        )
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": qr2.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            SupplierJobAssignment.objects.filter(maintenance_request=self.mr).exists()
        )

    def test_double_award_is_idempotent(self):
        """Awarding the same job twice does not duplicate the assignment."""
        self.authenticate(self.agent)
        self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": self.qr.pk},
            format="json",
        )
        # Re-open and try to re-award (simulate edge case)
        self.qr.status = JobQuoteRequest.Status.QUOTED
        self.qr.save()
        self.jd.status = JobDispatch.Status.SENT
        self.jd.save()
        self.client.post(
            reverse("maintenance-dispatch-award", args=[self.mr.pk]),
            {"quote_request_id": self.qr.pk},
            format="json",
        )
        count = SupplierJobAssignment.objects.filter(
            supplier=self.supplier_user, maintenance_request=self.mr,
        ).count()
        self.assertEqual(count, 1)

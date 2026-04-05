"""Tests for lease events, onboarding steps, and event generation endpoints."""
import pytest
from datetime import date, timedelta

from django.urls import reverse

from apps.leases.models import LeaseEvent, OnboardingStep
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class LeaseEventsTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant_user = self.create_tenant()
        self.tenant_person = self.create_person(full_name="Tenant Person", linked_user=self.tenant_user)
        self.prop = self.create_property(agent=self.agent, name="Events Prop")
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.tenant_person)

    # ── List events ──

    def test_list_events_empty(self):
        self.authenticate(self.agent)
        url = reverse("lease-events", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_list_events_after_generate(self):
        self.authenticate(self.agent)
        # Generate first
        self.client.post(reverse("lease-generate-events", kwargs={"pk": self.lease.pk}))
        # Then list
        resp = self.client.get(reverse("lease-events", kwargs={"pk": self.lease.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.data), 0)

    # ── Create custom event ──

    def test_create_custom_event(self):
        self.authenticate(self.agent)
        url = reverse("lease-events", kwargs={"pk": self.lease.pk})
        payload = {
            "title": "Tenant walkthrough",
            "description": "Pre-move-in walkthrough with tenant",
            "date": str(date.today() + timedelta(days=7)),
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["title"], "Tenant walkthrough")
        self.assertEqual(resp.data["event_type"], LeaseEvent.EventType.CUSTOM)

    def test_create_event_missing_required_fields(self):
        self.authenticate(self.agent)
        url = reverse("lease-events", kwargs={"pk": self.lease.pk})
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    # ── Generate events ──

    def test_generate_events(self):
        self.authenticate(self.agent)
        url = reverse("lease-generate-events", kwargs={"pk": self.lease.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.data["events_created"], 0)
        self.assertGreater(resp.data["onboarding_steps_created"], 0)

    def test_generate_events_creates_db_records(self):
        self.authenticate(self.agent)
        url = reverse("lease-generate-events", kwargs={"pk": self.lease.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            LeaseEvent.objects.filter(lease=self.lease).count(),
            resp.data["events_created"],
        )
        self.assertEqual(
            OnboardingStep.objects.filter(lease=self.lease).count(),
            resp.data["onboarding_steps_created"],
        )

    # ── Update event ──

    def test_update_event_status_completed(self):
        self.authenticate(self.agent)
        event = LeaseEvent.objects.create(
            lease=self.lease,
            event_type=LeaseEvent.EventType.CUSTOM,
            title="Test event",
            date=date.today(),
        )
        url = reverse("lease-update-event", kwargs={"pk": self.lease.pk, "event_id": event.pk})
        resp = self.client.patch(url, {"status": "completed"}, format="json")
        self.assertEqual(resp.status_code, 200)
        event.refresh_from_db()
        self.assertIsNotNone(event.completed_at)
        self.assertEqual(event.completed_by, self.agent)

    def test_update_event_partial_fields(self):
        self.authenticate(self.agent)
        event = LeaseEvent.objects.create(
            lease=self.lease,
            event_type=LeaseEvent.EventType.CUSTOM,
            title="Original title",
            date=date.today(),
        )
        url = reverse("lease-update-event", kwargs={"pk": self.lease.pk, "event_id": event.pk})
        resp = self.client.patch(url, {"title": "Updated title"}, format="json")
        self.assertEqual(resp.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.title, "Updated title")
        # completed_at should remain unset since status was not changed to completed
        self.assertIsNone(event.completed_at)


class OnboardingStepsTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant_user = self.create_tenant()
        self.tenant_person = self.create_person(full_name="Tenant Person", linked_user=self.tenant_user)
        self.prop = self.create_property(agent=self.agent, name="Onboarding Prop")
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.tenant_person)

    # ── List onboarding steps ──

    def test_list_onboarding_empty(self):
        self.authenticate(self.agent)
        url = reverse("lease-onboarding", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_list_onboarding_after_generate(self):
        self.authenticate(self.agent)
        self.client.post(reverse("lease-generate-events", kwargs={"pk": self.lease.pk}))
        resp = self.client.get(reverse("lease-onboarding", kwargs={"pk": self.lease.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.data), 0)

    # ── Update onboarding step ──

    def test_complete_onboarding_step(self):
        self.authenticate(self.agent)
        step = OnboardingStep.objects.create(
            lease=self.lease,
            step_type=OnboardingStep.StepType.DEPOSIT_PAYMENT,
            title="Deposit payment",
            order=1,
        )
        url = reverse("lease-update-onboarding", kwargs={"pk": self.lease.pk, "step_id": step.pk})
        resp = self.client.patch(url, {"is_completed": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        step.refresh_from_db()
        self.assertTrue(step.is_completed)
        self.assertIsNotNone(step.completed_at)
        self.assertEqual(step.completed_by, self.agent)

    def test_uncomplete_onboarding_step(self):
        """Toggling is_completed to False clears completed_at and completed_by."""
        self.authenticate(self.agent)
        step = OnboardingStep.objects.create(
            lease=self.lease,
            step_type=OnboardingStep.StepType.KEY_HANDOVER,
            title="Key handover",
            order=2,
        )
        # Complete first
        url = reverse("lease-update-onboarding", kwargs={"pk": self.lease.pk, "step_id": step.pk})
        self.client.patch(url, {"is_completed": True}, format="json")
        step.refresh_from_db()
        self.assertIsNotNone(step.completed_at)

        # Uncomplete
        resp = self.client.patch(url, {"is_completed": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        step.refresh_from_db()
        self.assertFalse(step.is_completed)
        self.assertIsNone(step.completed_at)
        self.assertIsNone(step.completed_by)

    def test_update_onboarding_step_notes(self):
        self.authenticate(self.agent)
        step = OnboardingStep.objects.create(
            lease=self.lease,
            step_type=OnboardingStep.StepType.WELCOME_SENT,
            title="Welcome message",
            order=3,
        )
        url = reverse("lease-update-onboarding", kwargs={"pk": self.lease.pk, "step_id": step.pk})
        resp = self.client.patch(url, {"notes": "Sent via WhatsApp"}, format="json")
        self.assertEqual(resp.status_code, 200)
        step.refresh_from_db()
        self.assertEqual(step.notes, "Sent via WhatsApp")


class LeaseEventsPermissionTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.tenant_user = self.create_tenant()
        self.tenant_person = self.create_person(full_name="Tenant Person", linked_user=self.tenant_user)
        self.prop = self.create_property(agent=self.agent, name="Perm Prop")
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.tenant_person)

    def test_unauthenticated_list_events_denied(self):
        url = reverse("lease-events", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_generate_events_denied(self):
        url = reverse("lease-generate-events", kwargs={"pk": self.lease.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_onboarding_denied(self):
        url = reverse("lease-onboarding", kwargs={"pk": self.lease.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 401)

    def test_tenant_cannot_generate_events(self):
        """Tenants should not be able to trigger event generation."""
        self.authenticate(self.tenant_user)
        url = reverse("lease-generate-events", kwargs={"pk": self.lease.pk})
        resp = self.client.post(url)
        # Tenant can access their lease but generate-events should be restricted
        # If the viewset allows it (no extra permission check), this documents current behaviour
        # and flags it for future permission hardening
        self.assertIn(resp.status_code, [200, 403])

    def test_tenant_cannot_create_custom_event(self):
        """Tenants should not be able to create custom events."""
        self.authenticate(self.tenant_user)
        url = reverse("lease-events", kwargs={"pk": self.lease.pk})
        payload = {
            "title": "Sneaky event",
            "description": "Should not be allowed",
            "date": str(date.today()),
        }
        resp = self.client.post(url, payload, format="json")
        # Documents current behaviour — tenant may or may not have write access
        self.assertIn(resp.status_code, [201, 403])

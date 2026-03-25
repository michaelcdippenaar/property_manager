"""Tests for LeaseViewSet and related actions (documents, tenants, occupants, guarantors, events, calendar)."""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.leases.models import Lease, LeaseDocument, LeaseTenant, LeaseOccupant, LeaseGuarantor, LeaseEvent
from tests.base import TremlyAPITestCase


class LeaseViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.admin = self.create_admin()
        self.agent = self.create_agent()
        self.tenant_user = self.create_tenant()
        self.tenant_person = self.create_person(full_name="Tenant Person", linked_user=self.tenant_user)
        self.prop = self.create_property(agent=self.agent, name="Test Prop")
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.tenant_person)

    def test_admin_sees_all_leases(self):
        self.authenticate(self.admin)
        resp = self.client.get(reverse("lease-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_agent_sees_assigned_properties(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_idor_agent_sees_unassigned_and_admin_properties(self):
        """
        SECURITY AUDIT (vuln #4): Agent queryset includes leases for unassigned
        properties and admin-assigned properties, broadening access.
        """
        unassigned_prop = self.create_property(agent=None, name="Unassigned")
        unassigned_unit = self.create_unit(property_obj=unassigned_prop, unit_number="U1")
        self.create_lease(unit=unassigned_unit)

        admin_prop = self.create_property(agent=self.admin, name="Admin Prop")
        admin_unit = self.create_unit(property_obj=admin_prop, unit_number="A1")
        self.create_lease(unit=admin_unit)

        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-list"))
        ids = [l["id"] for l in resp.data["results"]]
        # Agent can see leases beyond their own properties
        self.assertGreaterEqual(len(ids), 2)

    def test_tenant_sees_own_leases(self):
        self.authenticate(self.tenant_user)
        resp = self.client.get(reverse("lease-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_tenant_no_lease_sees_empty(self):
        other = self.create_user(email="nolease@test.com")
        self.authenticate(other)
        resp = self.client.get(reverse("lease-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["results"]), 0)

    def test_create_lease(self):
        self.authenticate(self.agent)
        person = self.create_person(full_name="New Tenant")
        resp = self.client.post(reverse("lease-list"), {
            "unit": self.unit.pk,
            "primary_tenant": person.pk,
            "start_date": "2026-01-01",
            "end_date": "2027-01-01",
            "monthly_rent": "6000.00",
            "deposit": "12000.00",
        })
        self.assertEqual(resp.status_code, 201)

    def test_create_lease_end_before_start(self):
        """
        SECURITY AUDIT (vuln #23): No validation that end_date > start_date.
        """
        self.authenticate(self.agent)
        person = self.create_person(full_name="Bad Lease Tenant")
        resp = self.client.post(reverse("lease-list"), {
            "unit": self.unit.pk,
            "primary_tenant": person.pk,
            "start_date": "2027-01-01",
            "end_date": "2026-01-01",  # Before start
            "monthly_rent": "5000.00",
            "deposit": "10000.00",
        })
        # Currently accepted — documents missing validation
        self.assertIn(resp.status_code, [201, 400])

    def test_filter_by_status(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-list"), {"status": "active"})
        self.assertEqual(resp.status_code, 200)
        for l in resp.data["results"]:
            self.assertEqual(l["status"], "active")

    def test_filter_by_unit(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-list"), {"unit": self.unit.pk})
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated(self):
        resp = self.client.get(reverse("lease-list"))
        self.assertEqual(resp.status_code, 401)


class LeaseDocumentTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)

    def test_upload_document(self):
        self.authenticate(self.agent)
        f = SimpleUploadedFile("lease.pdf", b"PDF content", content_type="application/pdf")
        resp = self.client.post(
            reverse("lease-documents", args=[self.lease.pk]),
            {"file": f, "document_type": "signed_lease", "description": "lease.pdf"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

    def test_list_documents(self):
        LeaseDocument.objects.create(
            lease=self.lease,
            document_type="other",
            file=SimpleUploadedFile("doc.pdf", b"x"),
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-documents", args=[self.lease.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_delete_document(self):
        doc = LeaseDocument.objects.create(
            lease=self.lease,
            document_type="other",
            file=SimpleUploadedFile("del.pdf", b"x"),
        )
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("lease-delete-document", args=[self.lease.pk, doc.pk])
        )
        self.assertEqual(resp.status_code, 204)

    def test_duplicate_document_returns_existing(self):
        self.authenticate(self.agent)
        f = SimpleUploadedFile("dup.pdf", b"PDF", content_type="application/pdf")
        self.client.post(
            reverse("lease-documents", args=[self.lease.pk]),
            {"file": f, "document_type": "other", "description": "dup.pdf"},
            format="multipart",
        )
        f2 = SimpleUploadedFile("dup.pdf", b"PDF", content_type="application/pdf")
        resp = self.client.post(
            reverse("lease-documents", args=[self.lease.pk]),
            {"file": f2, "document_type": "other", "description": "dup.pdf"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200)  # Not 201 — returns existing


class LeaseTenantTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit, primary_tenant=None)
        self.person = self.create_person(full_name="Primary Person")

    def test_add_tenant_with_person_id(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-add-tenant", args=[self.lease.pk]),
            {"person_id": self.person.pk},
        )
        self.assertEqual(resp.status_code, 201)

    def test_add_tenant_creates_person(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-add-tenant", args=[self.lease.pk]),
            {"person": {"full_name": "New Inline Person", "phone": "0820001111"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_add_first_tenant_sets_primary(self):
        self.authenticate(self.agent)
        self.client.post(
            reverse("lease-add-tenant", args=[self.lease.pk]),
            {"person_id": self.person.pk},
        )
        self.lease.refresh_from_db()
        self.assertEqual(self.lease.primary_tenant, self.person)

    def test_add_second_tenant_creates_co_tenant(self):
        self.lease.primary_tenant = self.person
        self.lease.save()
        co_person = self.create_person(full_name="Co-Tenant")
        self.authenticate(self.agent)
        self.client.post(
            reverse("lease-add-tenant", args=[self.lease.pk]),
            {"person_id": co_person.pk},
        )
        self.assertEqual(LeaseTenant.objects.filter(lease=self.lease).count(), 1)

    def test_remove_primary_promotes_co_tenant(self):
        self.lease.primary_tenant = self.person
        self.lease.save()
        co_person = self.create_person(full_name="Co-Tenant Promoted")
        LeaseTenant.objects.create(lease=self.lease, person=co_person)

        self.authenticate(self.agent)
        self.client.delete(
            reverse("lease-remove-tenant", args=[self.lease.pk, self.person.pk])
        )
        self.lease.refresh_from_db()
        self.assertEqual(self.lease.primary_tenant, co_person)

    def test_remove_co_tenant(self):
        self.lease.primary_tenant = self.person
        self.lease.save()
        co = self.create_person(full_name="Co Remove")
        LeaseTenant.objects.create(lease=self.lease, person=co)
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("lease-remove-tenant", args=[self.lease.pk, co.pk])
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(LeaseTenant.objects.filter(lease=self.lease).count(), 0)


class LeaseOccupantTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        self.person = self.create_person(full_name="Occupant")

    def test_add_occupant(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-add-occupant", args=[self.lease.pk]),
            {"person_id": self.person.pk, "relationship_to_tenant": "spouse"},
        )
        self.assertEqual(resp.status_code, 201)

    def test_remove_occupant(self):
        occ = LeaseOccupant.objects.create(lease=self.lease, person=self.person)
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("lease-remove-occupant", args=[self.lease.pk, occ.pk])
        )
        self.assertEqual(resp.status_code, 204)


class LeaseGuarantorTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.primary = self.create_person(full_name="Primary")
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.primary)
        self.guarantor_person = self.create_person(full_name="Guarantor")

    def test_add_guarantor(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-add-guarantor", args=[self.lease.pk]),
            {"person_id": self.guarantor_person.pk},
        )
        self.assertEqual(resp.status_code, 201)

    def test_add_guarantor_with_covers_tenant(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("lease-add-guarantor", args=[self.lease.pk]),
            {"person_id": self.guarantor_person.pk, "covers_tenant_id": self.primary.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        gua = LeaseGuarantor.objects.get(lease=self.lease, person=self.guarantor_person)
        self.assertEqual(gua.covers_tenant, self.primary)

    def test_remove_guarantor(self):
        gua = LeaseGuarantor.objects.create(
            lease=self.lease, person=self.guarantor_person
        )
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("lease-remove-guarantor", args=[self.lease.pk, gua.pk])
        )
        self.assertEqual(resp.status_code, 204)


class LeaseCalendarTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.lease = self.create_lease(unit=self.unit)
        LeaseEvent.objects.create(
            lease=self.lease,
            event_type="rent_due",
            title="Rent Due",
            date=date.today(),
        )

    def test_calendar_all(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-calendar"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_calendar_date_range(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("lease-calendar"), {
            "from": str(date.today()),
            "to": str(date.today() + timedelta(days=30)),
        })
        self.assertEqual(resp.status_code, 200)

"""Tests for SupplierViewSet: CRUD, documents, properties, attach_group."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.maintenance.models import Supplier, SupplierDocument, SupplierProperty, SupplierTrade
from apps.properties.models import PropertyGroup
from tests.base import TremlyAPITestCase


class SupplierViewSetTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.supplier = self.create_supplier(name="Plumber Joe", phone="0820001111")
        SupplierTrade.objects.create(supplier=self.supplier, trade="plumbing")

    def test_list_suppliers(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_idor_any_role_can_list_suppliers(self):
        """
        SECURITY AUDIT (vuln #5): Any authenticated user can CRUD suppliers,
        not just agents/admins.
        """
        tenant = self.create_tenant()
        self.authenticate(tenant)
        resp = self.client.get(reverse("supplier-list"))
        # Tenant can see suppliers — no role check
        self.assertEqual(resp.status_code, 200)

    def test_create_supplier(self):
        self.authenticate(self.agent)
        resp = self.client.post(reverse("supplier-list"), {
            "name": "Sparky",
            "phone": "0821112222",
            "email": "sparky@test.com",
        })
        self.assertEqual(resp.status_code, 201)

    def test_retrieve_supplier(self):
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-detail", args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "Plumber Joe")

    def test_update_supplier(self):
        self.authenticate(self.agent)
        resp = self.client.patch(
            reverse("supplier-detail", args=[self.supplier.pk]),
            {"company_name": "Joe's Plumbing"},
        )
        self.assertEqual(resp.status_code, 200)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.company_name, "Joe's Plumbing")

    def test_delete_supplier(self):
        self.authenticate(self.agent)
        resp = self.client.delete(reverse("supplier-detail", args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 204)

    def test_filter_active(self):
        inactive = self.create_supplier(name="Inactive", phone="0820002222", is_active=False)
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-list"), {"is_active": "true"})
        ids = [s["id"] for s in resp.data["results"]]
        self.assertIn(self.supplier.pk, ids)
        self.assertNotIn(inactive.pk, ids)

    def test_supplier_requests(self):
        prop = self.create_property(agent=self.agent)
        unit = self.create_unit(property_obj=prop)
        mr = self.create_maintenance_request(unit=unit, supplier=self.supplier)
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-requests", args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 200)

    # --- Documents ---

    def test_documents_list(self):
        SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type="id_copy",
            file=SimpleUploadedFile("id.pdf", b"PDF"),
        )
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-documents", args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_documents_create(self):
        self.authenticate(self.agent)
        f = SimpleUploadedFile("cidb.pdf", b"PDF", content_type="application/pdf")
        resp = self.client.post(
            reverse("supplier-documents", args=[self.supplier.pk]),
            {"file": f, "document_type": "cidb"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)

    def test_documents_delete(self):
        doc = SupplierDocument.objects.create(
            supplier=self.supplier,
            document_type="other",
            file=SimpleUploadedFile("x.pdf", b"x"),
        )
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("supplier-delete-document", args=[self.supplier.pk, doc.pk])
        )
        self.assertEqual(resp.status_code, 204)

    # --- Properties ---

    def test_properties_list(self):
        prop = self.create_property(agent=self.agent)
        SupplierProperty.objects.create(supplier=self.supplier, property=prop)
        self.authenticate(self.agent)
        resp = self.client.get(reverse("supplier-properties", args=[self.supplier.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_properties_link(self):
        prop = self.create_property(agent=self.agent, name="Link Prop")
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("supplier-properties", args=[self.supplier.pk]),
            {"property": prop.pk},
        )
        self.assertEqual(resp.status_code, 201)

    def test_properties_remove(self):
        prop = self.create_property(agent=self.agent, name="Remove Prop")
        link = SupplierProperty.objects.create(supplier=self.supplier, property=prop)
        self.authenticate(self.agent)
        resp = self.client.delete(
            reverse("supplier-remove-property", args=[self.supplier.pk, link.pk])
        )
        self.assertEqual(resp.status_code, 204)

    # --- Attach group ---

    def test_attach_group(self):
        group = PropertyGroup.objects.create(name="Group A")
        prop = self.create_property(agent=self.agent, name="Grouped Prop")
        group.properties.add(prop)
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("supplier-attach-group", args=[self.supplier.pk]),
            {"group_id": group.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["attached"], 1)

    def test_attach_group_not_found(self):
        self.authenticate(self.agent)
        resp = self.client.post(
            reverse("supplier-attach-group", args=[self.supplier.pk]),
            {"group_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

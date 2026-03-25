"""
Shared test helpers for the Tremly Property Manager test suite.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, Person
from apps.properties.models import Property, Unit, UnitInfo, PropertyAgentConfig, PropertyGroup
from apps.leases.models import (
    Lease, LeaseTemplate, LeaseBuilderSession, LeaseTenant,
    LeaseOccupant, LeaseGuarantor, ReusableClause, LeaseEvent, LeaseDocument,
)
from apps.maintenance.models import (
    Supplier, SupplierTrade, MaintenanceRequest, JobDispatch,
    JobQuoteRequest, JobQuote, MaintenanceSkill, AgentQuestion,
    MaintenanceActivity,
)
from apps.esigning.models import ESigningSubmission


class TremlyAPITestCase(APITestCase):
    """Base test class with factory helpers for all Tremly models."""

    # ── User factories ──

    def create_user(self, email="user@test.com", password="testpass123", role="tenant", **kwargs):
        return User.objects.create_user(email=email, password=password, role=role, **kwargs)

    def create_admin(self, email="admin@test.com", **kwargs):
        return self.create_user(email=email, role="admin", **kwargs)

    def create_agent(self, email="agent@test.com", **kwargs):
        return self.create_user(email=email, role="agent", **kwargs)

    def create_tenant(self, email="tenant@test.com", **kwargs):
        return self.create_user(email=email, role="tenant", **kwargs)

    def create_supplier_user(self, email="supplier@test.com", **kwargs):
        return self.create_user(email=email, role="supplier", **kwargs)

    def create_owner_user(self, email="owner@test.com", **kwargs):
        return self.create_user(email=email, role="owner", **kwargs)

    # ── Person factory ──

    def create_person(self, full_name="Test Person", linked_user=None, **kwargs):
        return Person.objects.create(full_name=full_name, linked_user=linked_user, **kwargs)

    # ── Property / Unit factories ──

    def create_property(self, agent=None, name="Test Property", **kwargs):
        defaults = {
            "property_type": "apartment",
            "address": "123 Test St",
            "city": "Cape Town",
            "province": "Western Cape",
            "postal_code": "8001",
        }
        defaults.update(kwargs)
        return Property.objects.create(agent=agent, name=name, **defaults)

    def create_unit(self, property_obj=None, unit_number="101", **kwargs):
        if property_obj is None:
            property_obj = self.create_property()
        defaults = {
            "bedrooms": 1,
            "bathrooms": 1,
            "rent_amount": Decimal("5000.00"),
            "status": "available",
        }
        defaults.update(kwargs)
        return Unit.objects.create(property=property_obj, unit_number=unit_number, **defaults)

    # ── Lease factory ──

    def create_lease(self, unit=None, primary_tenant=None, **kwargs):
        if unit is None:
            unit = self.create_unit()
        defaults = {
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=365),
            "monthly_rent": Decimal("5000.00"),
            "deposit": Decimal("10000.00"),
            "status": "active",
        }
        defaults.update(kwargs)
        return Lease.objects.create(unit=unit, primary_tenant=primary_tenant, **defaults)

    # ── Maintenance factories ──

    def create_maintenance_request(self, unit=None, tenant=None, **kwargs):
        if unit is None:
            unit = self.create_unit()
        if tenant is None:
            tenant = self.create_tenant(email=f"mr-tenant-{MaintenanceRequest.objects.count()}@test.com")
        defaults = {
            "title": "Leaking tap",
            "description": "The kitchen tap is leaking",
            "priority": "medium",
            "status": "open",
        }
        defaults.update(kwargs)
        return MaintenanceRequest.objects.create(unit=unit, tenant=tenant, **defaults)

    def create_supplier(self, name="Test Supplier", phone="0821234567", **kwargs):
        return Supplier.objects.create(name=name, phone=phone, **kwargs)

    # ── Auth helpers ──

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}

"""
TremlyAPITestCase — shared base class for all Tremly integration tests.

This is the single source of truth for test factory methods.
Import from here in all test files:

    from apps.test_hub.base.test_case import TremlyAPITestCase

Factory methods available:
    create_user(email, password, role, **kwargs)
    create_admin() / create_agent() / create_tenant()
    create_supplier_user() / create_owner_user()
    create_person(user=None, **kwargs)
    create_property(agent=None, **kwargs)
    create_unit(property_obj=None, **kwargs)
    create_lease(unit=None, tenant=None, **kwargs)
    create_maintenance_request(unit=None, tenant=None, **kwargs)
    authenticate(user) — force-authenticate the test client
    get_tokens(user) — return {access, refresh} JWT tokens
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, Person
from apps.properties.models import (
    Property, Unit, UnitInfo, PropertyAgentConfig, PropertyGroup,
    Landlord, BankAccount, PropertyOwnership,
)
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


class _JsonAPIClient(APIClient):
    """APIClient subclass that always negotiates JSON.

    DRF's default APIClient sends ``Accept: */*`` which causes the browsable
    HTML renderer to fire whenever a browser-like request comes in.  This
    subclass forces ``Accept: application/json`` on every request so test
    assertions can always call ``resp.json()`` without wrapping in
    ``HTTP_ACCEPT`` kwargs on every call.
    """

    def request(self, **kwargs):
        kwargs.setdefault("HTTP_ACCEPT", "application/json")
        return super().request(**kwargs)


class TremlyAPITestCase(APITestCase):
    """Base test class with factory helpers for all Tremly models."""

    client_class = _JsonAPIClient

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

    # ── Landlord / Ownership / Banking factories ──

    def create_landlord(self, name="Test Landlord (Pty) Ltd", **kwargs):
        defaults = {
            "landlord_type": "company",
            "email": "landlord@test.com",
            "phone": "0211234567",
            "registration_number": "2020/123456/07",
            "vat_number": "4123456789",
            "representative_name": "John Landlord",
            "representative_id_number": "8001015800083",
            "representative_email": "john@landlord.co.za",
            "representative_phone": "0829998877",
            "address": {"street": "10 Main Rd", "city": "Cape Town", "province": "Western Cape", "postal_code": "8001"},
        }
        defaults.update(kwargs)
        return Landlord.objects.create(name=name, **defaults)

    def create_bank_account(self, landlord=None, **kwargs):
        if landlord is None:
            landlord = self.create_landlord()
        defaults = {
            "bank_name": "First National Bank",
            "branch_code": "250655",
            "account_number": "62012345678",
            "account_type": "Cheque",
            "account_holder": "Test Landlord (Pty) Ltd",
            "is_default": True,
        }
        defaults.update(kwargs)
        return BankAccount.objects.create(landlord=landlord, **defaults)

    def create_property_ownership(self, property_obj=None, landlord=None, **kwargs):
        if property_obj is None:
            property_obj = self.create_property()
        defaults = {
            "owner_name": "Test Landlord (Pty) Ltd",
            "owner_type": "company",
            "owner_email": "landlord@test.com",
            "is_current": True,
            "start_date": date.today() - timedelta(days=365),
        }
        defaults.update(kwargs)
        return PropertyOwnership.objects.create(property=property_obj, landlord=landlord, **defaults)

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
            # RHA s5(3) required fields — keep defaults non-empty so the RHA gate
            # passes in tests that are not specifically testing RHA validation.
            "notice_period_days": 30,
            "escalation_clause": "Rent escalates annually in line with CPI.",
            "renewal_clause": "Lease renews on mutual written agreement.",
            "domicilium_address": "123 Test St, Cape Town, 8001",
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

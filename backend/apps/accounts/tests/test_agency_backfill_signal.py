"""Regression: ``_backfill_agency_id_from_parent`` pre_save receiver.

The signal is the safety net under every code path that creates a row
with a parent FK but forgets to stamp ``agency_id``. It opts in per model
via the ``AGENCY_PARENT_FIELD`` class attribute.

These tests don't go through the API — they exercise the bare model
``objects.create(...)`` calls that were the source of the silent
``agency_id=NULL`` orphans the CTO audit found.
"""
from __future__ import annotations

import pytest
from django.test import TestCase

from apps.accounts.models import Agency
from apps.properties.models import (
    BankAccount,
    Landlord,
    LandlordDocument,
    Property,
    PropertyAgentAssignment,
    PropertyDocument,
    PropertyPhoto,
)


pytestmark = [pytest.mark.integration]


class AgencyBackfillSignalTest(TestCase):
    """``pre_save`` copies ``agency_id`` from the declared parent FK when
    the row is saved without one. Covers each pair flagged in the audit
    (PropertyAgentAssignment, PropertyPhoto, PropertyDocument,
    LandlordDocument, BankAccount) plus the structural primitive."""

    @classmethod
    def setUpTestData(cls):
        cls.agency = Agency.objects.create(name="Backfill Test Agency")
        cls.property = Property.objects.create(
            name="A Test Property",
            property_type="apartment",
            address="1 Test St",
            city="Cape Town",
            province="Western Cape",
            postal_code="8001",
            agency=cls.agency,
        )
        cls.landlord = Landlord.objects.create(
            name="A Test Landlord (Pty) Ltd",
            landlord_type="company",
            email="ll@test.test",
            agency=cls.agency,
        )

    # ── Property-rooted ──

    def test_property_agent_assignment_inherits_agency(self):
        """The PropertySerializer.create() bug — auto-creating an
        assignment without explicit agency_id — must self-heal."""
        from apps.accounts.models import User
        agent = User.objects.create_user(
            email="agent@backfill.test", password="x", role="agent", agency=self.agency,
        )
        a = PropertyAgentAssignment.objects.create(
            property=self.property, agent=agent,
        )  # NOTE: no agency=
        assert a.agency_id == self.agency.pk, (
            "PropertyAgentAssignment did not inherit agency_id from "
            "its property FK. The pre_save backfill receiver isn't firing."
        )

    def test_property_photo_inherits_agency(self):
        p = PropertyPhoto.objects.create(property=self.property, caption="x")
        assert p.agency_id == self.agency.pk

    def test_property_document_inherits_agency(self):
        d = PropertyDocument.objects.create(
            property=self.property,
            doc_type=PropertyDocument.DocType.OTHER,
        )
        assert d.agency_id == self.agency.pk

    # ── Landlord-rooted ──

    def test_landlord_document_inherits_agency(self):
        d = LandlordDocument.objects.create(landlord=self.landlord)
        assert d.agency_id == self.agency.pk

    def test_bank_account_inherits_agency(self):
        ba = BankAccount.objects.create(
            landlord=self.landlord,
            bank_name="Test Bank",
            branch_code="000000",
            account_number="123",
            account_type="Cheque",
            account_holder="Test",
        )
        assert ba.agency_id == self.agency.pk

    # ── Negative cases ──

    def test_existing_agency_id_is_not_overwritten(self):
        """If a row is saved with an explicit agency_id, the signal must
        leave it alone — never overwrite. Admins creating-on-behalf of
        another agency rely on this."""
        other_agency = Agency.objects.create(name="Other Agency")
        ba = BankAccount.objects.create(
            landlord=self.landlord,
            bank_name="Test Bank",
            branch_code="000000",
            account_number="123",
            account_type="Cheque",
            account_holder="Test",
            agency=other_agency,   # explicit, different from parent
        )
        assert ba.agency_id == other_agency.pk, (
            "Backfill receiver overwrote an explicitly-set agency_id."
        )

    def test_orphan_parent_does_not_backfill(self):
        """If the parent itself has agency_id=NULL (data corruption case),
        the child is left null too — better than silently propagating
        a bad value."""
        orphan_landlord = Landlord.objects.create(
            name="No agency landlord",
            landlord_type="individual",
            email="orphan@test.test",
            agency=None,  # deliberately
        )
        d = LandlordDocument.objects.create(landlord=orphan_landlord)
        assert d.agency_id is None

"""
Tests for N+1 query elimination via select_related in the esigning signing flow.

RNT-QUAL-029: _resolve_link must pre-fetch lease__unit__property AND
mandate__property in a single query so that _notify_staff and
_email_signed_copy_to_signers never issue extra queries.
"""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.esigning.models import ESigningPublicLink, ESigningSubmission
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


def _make_signers():
    return [
        {
            "id": 1,
            "name": "Owner",
            "email": "owner@test.com",
            "role": "landlord",
            "status": "sent",
            "order": 0,
        }
    ]


class TestResolveLinkselectRelatedMandate(TremlyAPITestCase):
    """
    _resolve_link must load submission__mandate__property in the initial
    query so that _notify_staff / _email_signed_copy_to_signers do not fire
    extra DB hits when accessing mandate.property.name.
    """

    def _create_mandate_submission_and_link(self):
        from apps.properties.models import RentalMandate
        agent = self.create_agent(email="agent-srq@test.com")
        prop = self.create_property(agent=agent, name="Mandate Property")
        mandate = RentalMandate.objects.create(
            property=prop,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            exclusivity=RentalMandate.Exclusivity.SOLE,
            commission_rate="8.00",
            commission_period=RentalMandate.CommissionPeriod.MONTHLY,
            start_date=timezone.now().date(),
        )
        submission = ESigningSubmission.objects.create(
            mandate=mandate,
            status=ESigningSubmission.Status.PENDING,
            signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signers=_make_signers(),
            created_by=agent,
        )
        link = ESigningPublicLink.objects.create(
            submission=submission,
            signer_role="landlord",
            expires_at=timezone.now() + timedelta(days=14),
        )
        return link, submission, prop

    def test_resolve_link_mandate_no_extra_query_for_property(self):
        """
        After _resolve_link returns, accessing sub.mandate.property must NOT
        fire an extra SQL query (it should already be cached via select_related).
        """
        link, submission, prop = self._create_mandate_submission_and_link()

        from apps.esigning.views import ESigningPublicSignDetailView

        view = ESigningPublicSignDetailView()

        # Resolve the link — this performs one SELECT with the join.
        resolved_link, sub, signer, error = view._resolve_link(link.pk)
        self.assertIsNone(error, "Link resolution should succeed")
        self.assertIsNotNone(sub)

        # Now access mandate.property in zero extra queries.
        with self.assertNumQueries(0):
            prop_name = sub.mandate.property.name

        self.assertEqual(prop_name, "Mandate Property")

    def test_resolve_link_mandate_property_name_correct(self):
        """
        Smoke-check: resolved sub.mandate.property.name matches the created property.
        """
        link, submission, prop = self._create_mandate_submission_and_link()

        from apps.esigning.views import ESigningPublicSignDetailView

        view = ESigningPublicSignDetailView()
        resolved_link, sub, signer, error = view._resolve_link(link.pk)
        self.assertIsNone(error)
        self.assertEqual(sub.mandate.property.name, "Mandate Property")


class TestResolveLinkselectRelatedLease(TremlyAPITestCase):
    """
    Regression: lease path was already joined; confirm it still works and
    also fires zero extra queries after _resolve_link.
    """

    def _create_lease_submission_and_link(self):
        agent = self.create_agent(email="agent-srql@test.com")
        prop = self.create_property(agent=agent, name="Lease Property")
        unit = self.create_unit(property_obj=prop)
        lease = self.create_lease(unit=unit, status="pending")
        submission = ESigningSubmission.objects.create(
            lease=lease,
            status=ESigningSubmission.Status.PENDING,
            signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signers=_make_signers(),
            created_by=agent,
        )
        link = ESigningPublicLink.objects.create(
            submission=submission,
            signer_role="landlord",
            expires_at=timezone.now() + timedelta(days=14),
        )
        return link, submission, prop, unit

    def test_resolve_link_lease_no_extra_query_for_unit_property(self):
        """
        After _resolve_link, accessing sub.lease.unit.property must fire no
        additional SQL (already joined via select_related).
        """
        link, submission, prop, unit = self._create_lease_submission_and_link()

        from apps.esigning.views import ESigningPublicSignDetailView

        view = ESigningPublicSignDetailView()
        resolved_link, sub, signer, error = view._resolve_link(link.pk)
        self.assertIsNone(error)

        with self.assertNumQueries(0):
            prop_name = sub.lease.unit.property.name

        self.assertEqual(prop_name, "Lease Property")

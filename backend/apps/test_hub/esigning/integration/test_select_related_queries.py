"""
Tests for N+1 query elimination via select_related in the esigning signing flow.

RNT-QUAL-029: _resolve_link must pre-fetch lease__unit__property AND
mandate__property in a single query so that _notify_staff and
_email_signed_copy_to_signers never issue extra queries.

RNT-QUAL-014: complete_native_signer() must also pre-join related objects on its
select_for_update re-fetch so the helper functions fired after signing completion
never trigger additional per-call DB queries.
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


# ── RNT-QUAL-014: complete_native_signer select_related ──────────────────────


class TestCompleteNativeSignerSelectRelated(TremlyAPITestCase):
    """
    complete_native_signer() re-fetches ESigningSubmission with select_for_update.
    After the fix it must also join lease__unit__property and mandate__property so
    the helper functions (_notify_staff, _email_signed_copy_to_signers) that access
    those relations do not fire additional SQL queries.
    """

    def _make_mandate_submission(self):
        """Create a mandate + submission + minimal document content for signing."""
        import hashlib
        from apps.properties.models import RentalMandate

        agent = self.create_agent(email="agent-cns-srq@test.com")
        prop = self.create_property(agent=agent, name="CNS Mandate Property")
        mandate = RentalMandate.objects.create(
            property=prop,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            exclusivity=RentalMandate.Exclusivity.SOLE,
            commission_rate="8.00",
            commission_period=RentalMandate.CommissionPeriod.MONTHLY,
            start_date=timezone.now().date(),
        )
        doc_html = "<p>Mandate document</p>"
        doc_hash = hashlib.sha256(doc_html.encode()).hexdigest()
        submission = ESigningSubmission.objects.create(
            mandate=mandate,
            status=ESigningSubmission.Status.PENDING,
            signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signers=[
                {
                    "id": 1,
                    "name": "Owner",
                    "email": "owner@cns-test.com",
                    "role": "landlord",
                    "status": "sent",
                    "order": 0,
                }
            ],
            document_html=doc_html,
            document_hash=doc_hash,
            created_by=agent,
        )
        return submission, prop

    def test_complete_native_signer_mandate_no_extra_query_for_property(self):
        """
        After complete_native_signer() returns, accessing sub.mandate.property must
        NOT fire an extra SQL query (already joined via select_related in the
        select_for_update re-fetch).
        """
        from apps.esigning.services import complete_native_signer

        submission, prop = self._make_mandate_submission()

        signed_fields = [
            {"fieldName": "signature_landlord", "fieldType": "signature", "imageData": "data:image/png;base64,AA=="}
        ]
        audit_data = {
            "ip_address": "127.0.0.1",
            "user_agent": "test",
            "consent_given_at": timezone.now().isoformat(),
        }

        updated_sub, all_completed = complete_native_signer(
            submission, "landlord", signed_fields, audit_data
        )

        self.assertTrue(all_completed)

        # Accessing mandate.property must not trigger an additional SELECT.
        with self.assertNumQueries(0):
            prop_name = updated_sub.mandate.property.name

        self.assertEqual(prop_name, "CNS Mandate Property")

    def test_complete_native_signer_lease_no_extra_query_for_property(self):
        """
        After complete_native_signer() returns, accessing sub.lease.unit.property
        must NOT fire extra SQL queries.
        """
        import hashlib
        from apps.esigning.services import complete_native_signer

        agent = self.create_agent(email="agent-cns-lease-srq@test.com")
        prop = self.create_property(agent=agent, name="CNS Lease Property")
        unit = self.create_unit(property_obj=prop)
        lease = self.create_lease(unit=unit, status="pending")

        doc_html = "<p>Lease document</p>"
        doc_hash = hashlib.sha256(doc_html.encode()).hexdigest()
        submission = ESigningSubmission.objects.create(
            lease=lease,
            status=ESigningSubmission.Status.PENDING,
            signing_mode=ESigningSubmission.SigningMode.SEQUENTIAL,
            signing_backend=ESigningSubmission.SigningBackend.NATIVE,
            signers=[
                {
                    "id": 1,
                    "name": "Tenant",
                    "email": "tenant@cns-test.com",
                    "role": "tenant",
                    "status": "sent",
                    "order": 0,
                }
            ],
            document_html=doc_html,
            document_hash=doc_hash,
            created_by=agent,
        )

        signed_fields = [
            {"fieldName": "signature_tenant", "fieldType": "signature", "imageData": "data:image/png;base64,AA=="}
        ]
        audit_data = {
            "ip_address": "127.0.0.1",
            "user_agent": "test",
            "consent_given_at": timezone.now().isoformat(),
        }

        updated_sub, all_completed = complete_native_signer(
            submission, "tenant", signed_fields, audit_data
        )

        self.assertTrue(all_completed)

        # Accessing lease.unit.property must not trigger additional SELECTs.
        with self.assertNumQueries(0):
            prop_name = updated_sub.lease.unit.property.name

        self.assertEqual(prop_name, "CNS Lease Property")

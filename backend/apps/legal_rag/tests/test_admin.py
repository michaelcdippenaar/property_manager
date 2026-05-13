"""Tests for ``apps.legal_rag.admin``.

The admin registrations encode the source-of-truth rule: YAML PRs are
how legal facts change, not the Django admin UI. Tests pin the
read-only / append-only invariants so a future "let's make admin
editable" refactor visibly breaks here.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from django.contrib import admin as django_admin
from django.test import SimpleTestCase, TestCase

from apps.legal_rag.admin import (
    LegalAttestationAdmin,
    LegalCorpusVersionAdmin,
    LegalFactAdmin,
    LegalFactVersionAdmin,
)
from apps.legal_rag.models import (
    LegalAttestation,
    LegalCorpusVersion,
    LegalFact,
    LegalFactVersion,
)


class RegistrationTests(SimpleTestCase):
    """All four models registered with the right ModelAdmin subclass."""

    def test_all_four_models_registered(self):
        registered = django_admin.site._registry
        self.assertIn(LegalFact, registered)
        self.assertIn(LegalFactVersion, registered)
        self.assertIn(LegalAttestation, registered)
        self.assertIn(LegalCorpusVersion, registered)

    def test_legal_fact_uses_readonly_admin(self):
        self.assertIsInstance(
            django_admin.site._registry[LegalFact], LegalFactAdmin
        )

    def test_legal_fact_version_uses_readonly_admin(self):
        self.assertIsInstance(
            django_admin.site._registry[LegalFactVersion], LegalFactVersionAdmin
        )

    def test_legal_attestation_uses_append_only_admin(self):
        self.assertIsInstance(
            django_admin.site._registry[LegalAttestation], LegalAttestationAdmin
        )

    def test_legal_corpus_version_uses_readonly_admin(self):
        self.assertIsInstance(
            django_admin.site._registry[LegalCorpusVersion],
            LegalCorpusVersionAdmin,
        )


class ReadOnlyAdminPermissionTests(SimpleTestCase):
    """``LegalFact`` / ``LegalFactVersion`` / ``LegalCorpusVersion`` admins
    refuse add / change / delete unconditionally."""

    def _fake_request(self) -> MagicMock:
        req = MagicMock()
        req.user.is_superuser = True  # Even superusers blocked.
        return req

    def test_fact_admin_blocks_all_writes(self):
        admin_obj = django_admin.site._registry[LegalFact]
        req = self._fake_request()
        self.assertFalse(admin_obj.has_add_permission(req))
        self.assertFalse(admin_obj.has_change_permission(req))
        self.assertFalse(admin_obj.has_delete_permission(req))

    def test_version_admin_blocks_all_writes(self):
        admin_obj = django_admin.site._registry[LegalFactVersion]
        req = self._fake_request()
        self.assertFalse(admin_obj.has_add_permission(req))
        self.assertFalse(admin_obj.has_change_permission(req))
        self.assertFalse(admin_obj.has_delete_permission(req))

    def test_corpus_version_admin_blocks_all_writes(self):
        admin_obj = django_admin.site._registry[LegalCorpusVersion]
        req = self._fake_request()
        self.assertFalse(admin_obj.has_add_permission(req))
        self.assertFalse(admin_obj.has_change_permission(req))
        self.assertFalse(admin_obj.has_delete_permission(req))


class AppendOnlyAttestationAdminTests(TestCase):
    """``LegalAttestation`` admin allows add + view but never edit or delete."""

    def _fake_request(self) -> MagicMock:
        req = MagicMock()
        req.user.is_superuser = True
        return req

    def test_add_is_allowed(self):
        admin_obj = django_admin.site._registry[LegalAttestation]
        self.assertTrue(admin_obj.has_add_permission(self._fake_request()))

    def test_delete_is_forbidden(self):
        admin_obj = django_admin.site._registry[LegalAttestation]
        self.assertFalse(admin_obj.has_delete_permission(self._fake_request()))

    def test_add_page_has_editable_fields(self):
        """On the 'add' page (obj=None), readonly fields should be empty."""
        admin_obj = django_admin.site._registry[LegalAttestation]
        self.assertEqual(
            list(admin_obj.get_readonly_fields(self._fake_request(), obj=None)),
            [],
        )

    def test_change_page_freezes_every_field(self):
        """On the 'change' page (obj=existing), every field becomes readonly.

        This mirrors the model-layer ``save()`` raise on update — admin
        users should never see a Save button that would only fail at submit.
        """
        attestation = LegalAttestation.objects.create(
            attestation_id="test-2026-q2",
            attorney_name="Adv. Q. Test",
            attorney_admission_number="LPC-WC-99999",
            attorney_firm="Test Attorneys",
            attestation_method="counsel_opinion_letter",
            attestation_date=date(2026, 6, 15),
            scope="Test scope",
            cost_zar=0,
            facts_attested=[],
        )
        admin_obj = django_admin.site._registry[LegalAttestation]
        readonly = admin_obj.get_readonly_fields(self._fake_request(), obj=attestation)
        # Every model field should be readonly on edit.
        model_field_names = {f.name for f in LegalAttestation._meta.fields}
        self.assertEqual(set(readonly), model_field_names)

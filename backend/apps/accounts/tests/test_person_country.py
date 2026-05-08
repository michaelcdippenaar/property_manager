"""
Tests for Person.country and Person.phone_country_code (Feature 1).
"""
from __future__ import annotations

import pytest
from django.test import TestCase

from apps.accounts.models import Agency, Person


@pytest.mark.django_db
class TestPersonCountryFields(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency")

    def test_person_defaults_to_za(self):
        p = Person.objects.create(agency=self.agency, full_name="Themba Test")
        self.assertEqual(p.country, "ZA")
        self.assertEqual(p.phone_country_code, "+27")

    def test_person_accepts_other_country(self):
        p = Person.objects.create(
            agency=self.agency,
            full_name="Jane UK",
            country="GB",
            phone_country_code="+44",
        )
        self.assertEqual(p.country, "GB")
        self.assertEqual(p.phone_country_code, "+44")

    def test_person_blank_country_allowed(self):
        # blank=True allows empty values
        p = Person.objects.create(
            agency=self.agency,
            full_name="Anon",
            country="",
            phone_country_code="",
        )
        self.assertEqual(p.country, "")
        self.assertEqual(p.phone_country_code, "")

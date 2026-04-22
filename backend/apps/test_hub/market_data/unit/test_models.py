"""
Unit tests for apps.market_data models and area/source/type enums.

Run without DB.
"""
import pytest
from unittest.mock import MagicMock
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestAreaSlug:
    def test_stellenbosch_exists(self):
        from apps.market_data.models import AreaSlug
        assert "stellenbosch" in [a.value for a in AreaSlug]

    def test_city_bowl_exists(self):
        from apps.market_data.models import AreaSlug
        assert "city_bowl" in [a.value for a in AreaSlug]


class TestAreaLists:
    def test_cape_peninsula_areas_non_empty(self):
        from apps.market_data.models import CAPE_PENINSULA_AREAS
        assert len(CAPE_PENINSULA_AREAS) > 0

    def test_winelands_areas_non_empty(self):
        from apps.market_data.models import WINELANDS_AREAS
        assert len(WINELANDS_AREAS) > 0

    def test_all_areas_is_string_list(self):
        from apps.market_data.models import ALL_AREAS
        assert all(isinstance(a, str) for a in ALL_AREAS)


class TestSourceSlug:
    def test_property24_exists(self):
        from apps.market_data.models import SourceSlug
        assert "property24" in [s.value for s in SourceSlug]

    def test_private_property_exists(self):
        from apps.market_data.models import SourceSlug
        assert "private_property" in [s.value for s in SourceSlug]


class TestListingType:
    def test_rent_and_sale_choices(self):
        from apps.market_data.models import ListingType
        values = [c[0] for c in ListingType.choices]
        assert "rent" in values
        assert "sale" in values


class TestPropertyType:
    def test_apartment_and_house_exist(self):
        from apps.market_data.models import PropertyType
        values = [c[0] for c in PropertyType.choices]
        assert "apartment" in values
        assert "house" in values

"""
Unit tests for the supplier matching algorithm in apps/maintenance/matching.py.

All DB calls are mocked. Tests verify the scoring logic and sort order.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


def _make_supplier(
    supplier_id=1,
    name="Test Supplier",
    trades=None,
    latitude=None,
    longitude=None,
    service_radius_km=None,
    rating=None,
):
    """Build a mock Supplier object."""
    supplier = MagicMock()
    supplier.id = supplier_id
    supplier.name = name
    supplier.company_name = ""
    supplier.display_name = name
    supplier.phone = "0820001111"
    supplier.city = "Cape Town"
    supplier.trade_list = trades or []
    supplier.latitude = latitude
    supplier.longitude = longitude
    supplier.service_radius_km = service_radius_km
    supplier.rating = rating
    return supplier


def _make_maintenance_request(category="plumbing"):
    """Build a mock MaintenanceRequest with a unit/property."""
    prop = MagicMock()
    prop.latitude = None
    prop.longitude = None
    unit = MagicMock()
    unit.property = prop
    mr = MagicMock()
    mr.unit = unit
    mr.category = category
    return mr


class TestRankSuppliersReturnsSortedList:
    """rank_suppliers() returns results sorted by score descending."""

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_returns_list(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        mock_supplier_qs.filter.return_value.prefetch_related.return_value = []
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request()
        result = rank_suppliers(mr)
        assert isinstance(result, list)

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_empty_suppliers_returns_empty_list(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        mock_supplier_qs.filter.return_value.prefetch_related.return_value = []
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request()
        result = rank_suppliers(mr)
        assert result == []

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_results_sorted_by_score_descending(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        # Two suppliers: one with matching trade, one without
        plumber = _make_supplier(supplier_id=1, name="Plumber", trades=["plumbing"])
        painter = _make_supplier(supplier_id=2, name="Painter", trades=["painting"])

        mock_supplier_qs.filter.return_value.prefetch_related.return_value = [plumber, painter]
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_quote_qs.filter.return_value.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request(category="plumbing")
        result = rank_suppliers(mr)

        assert len(result) == 2
        # Plumber should score higher (trade match)
        assert result[0]["supplier_id"] == 1
        # Results must be in descending score order
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_matching_trade_scores_higher_than_mismatch(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        plumber = _make_supplier(supplier_id=1, name="Plumber", trades=["plumbing"])
        electrician = _make_supplier(supplier_id=2, name="Electrician", trades=["electrical"])

        mock_supplier_qs.filter.return_value.prefetch_related.return_value = [plumber, electrician]
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_quote_qs.filter.return_value.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request(category="plumbing")
        result = rank_suppliers(mr)

        plumber_result = next(r for r in result if r["supplier_id"] == 1)
        electrician_result = next(r for r in result if r["supplier_id"] == 2)
        assert plumber_result["score"] > electrician_result["score"]

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_result_contains_required_keys(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        supplier = _make_supplier(supplier_id=1, trades=["plumbing"])
        mock_supplier_qs.filter.return_value.prefetch_related.return_value = [supplier]
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_quote_qs.filter.return_value.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request()
        result = rank_suppliers(mr)

        assert len(result) == 1
        entry = result[0]
        assert "supplier_id" in entry
        assert "supplier_name" in entry
        assert "score" in entry
        assert "reasons" in entry
        assert "trades" in entry

    @patch("apps.maintenance.matching.SupplierProperty.objects")
    @patch("apps.maintenance.matching.JobQuote.objects")
    @patch("apps.maintenance.matching.Supplier.objects")
    def test_top_n_limits_results(self, mock_supplier_qs, mock_quote_qs, mock_prop_qs):
        from apps.maintenance.matching import rank_suppliers

        suppliers = [_make_supplier(supplier_id=i, trades=["plumbing"]) for i in range(20)]
        mock_supplier_qs.filter.return_value.prefetch_related.return_value = suppliers
        mock_quote_qs.aggregate.return_value = {"avg": None}
        mock_quote_qs.filter.return_value.aggregate.return_value = {"avg": None}
        mock_prop_qs.filter.return_value.values_list.return_value = []

        mr = _make_maintenance_request()
        result = rank_suppliers(mr, top_n=5)
        assert len(result) <= 5


class TestHaversineKm:
    """haversine_km() distance calculation."""

    def test_same_point_zero_distance(self):
        from apps.maintenance.matching import haversine_km
        dist = haversine_km(-33.9, 18.4, -33.9, 18.4)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self):
        """Cape Town CBD to Stellenbosch is approx 50km."""
        from apps.maintenance.matching import haversine_km
        dist = haversine_km(-33.925, 18.424, -33.934, 18.861)
        assert 40 < dist < 60  # rough sanity check

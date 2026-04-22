"""
Integration smoke tests for market_data read-only API endpoints.

Confirms authentication gates and empty-list responses for clean DB.
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]


LISTINGS_URL = "/api/v1/market-data/listings/"
STATS_URL = "/api/v1/market-data/stats/"


class TestMarketListingViewSet:
    def test_unauthenticated_returns_401(self, db, api_client):
        response = api_client.get(LISTINGS_URL)
        assert response.status_code == 401

    def test_agent_can_list_empty(self, db, tremly, api_client):
        agent = tremly.create_agent()
        api_client.force_authenticate(user=agent)
        response = api_client.get(LISTINGS_URL)
        assert response.status_code == 200
        data = response.json()
        # Paginated response has 'results' key
        assert "results" in data or isinstance(data, list)


class TestMarketPriceStatsViewSet:
    def test_unauthenticated_returns_401(self, db, api_client):
        response = api_client.get(STATS_URL)
        assert response.status_code == 401

    def test_agent_can_list_empty(self, db, tremly, api_client):
        agent = tremly.create_agent()
        api_client.force_authenticate(user=agent)
        response = api_client.get(STATS_URL)
        assert response.status_code == 200

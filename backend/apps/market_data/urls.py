from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.market_data.views import (
    AreaNewsViewSet,
    MapExportView,
    MarketListingViewSet,
    MarketPriceStatsViewSet,
    MunicipalBylawViewSet,
    ScrapeRunViewSet,
    SemanticSearchView,
)

router = DefaultRouter()
router.register("listings", MarketListingViewSet, basename="market-listing")
router.register("stats", MarketPriceStatsViewSet, basename="market-stats")
router.register("scrape-runs", ScrapeRunViewSet, basename="scrape-run")
router.register("news", AreaNewsViewSet, basename="area-news")
router.register("bylaws", MunicipalBylawViewSet, basename="municipal-bylaw")

urlpatterns = [
    path("", include(router.urls)),
    path("search/", SemanticSearchView.as_view(), name="market-search"),
    path("map-export/", MapExportView.as_view(), name="market-map-export"),
]

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.market_data.filters import (
    AreaNewsFilter,
    MarketListingFilter,
    MarketPriceStatsFilter,
    MunicipalBylawFilter,
    ScrapeRunFilter,
)
from apps.market_data.models import (
    AreaNewsArticle,
    MarketListing,
    MarketPriceStats,
    MunicipalBylaw,
    ScrapeRun,
    WINELANDS_AREAS,
)
from apps.market_data.serializers import (
    AreaNewsArticleSerializer,
    MarketListingDetailSerializer,
    MarketListingListSerializer,
    MarketPriceStatsSerializer,
    MunicipalBylawSerializer,
    ScrapeRunSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class MarketListingViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = MarketListingFilter
    search_fields = ["title", "suburb", "raw_address", "description"]
    ordering_fields = ["asking_price", "rental_price", "bedrooms", "floor_size_m2", "first_seen_at", "last_seen_at"]
    ordering = ["-last_seen_at"]
    pagination_class = StandardPagination

    def get_queryset(self):
        return MarketListing.objects.select_related("agency").prefetch_related("photos")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MarketListingDetailSerializer
        return MarketListingListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class MarketPriceStatsViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MarketPriceStats.objects.all()
    serializer_class = MarketPriceStatsSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = MarketPriceStatsFilter
    ordering_fields = ["date", "area", "avg_price", "sample_count"]
    ordering = ["-date", "area"]
    pagination_class = StandardPagination


class ScrapeRunViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ScrapeRun.objects.all()
    serializer_class = ScrapeRunSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = ScrapeRunFilter
    ordering = ["-started_at"]
    pagination_class = StandardPagination


class AreaNewsViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AreaNewsArticle.objects.all()
    serializer_class = AreaNewsArticleSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = AreaNewsFilter
    search_fields = ["title", "content_summary"]
    ordering_fields = ["published_at"]
    ordering = ["-published_at"]
    pagination_class = StandardPagination


class MunicipalBylawViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MunicipalBylaw.objects.all()
    serializer_class = MunicipalBylawSerializer
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = MunicipalBylawFilter
    search_fields = ["title", "content_text"]
    pagination_class = StandardPagination


class SemanticSearchView(APIView):
    """
    POST /api/v1/market-data/search/
    Body: {"query": "...", "area": "stellenbosch", "listing_type": "rent", "n_results": 10}
    Returns: ranked MarketListing results by semantic similarity.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "query is required"}, status=status.HTTP_400_BAD_REQUEST)

        area = request.data.get("area")
        listing_type = request.data.get("listing_type")
        n_results = int(request.data.get("n_results", 10))

        try:
            from core.contract_rag import get_market_listings_collection
            collection = get_market_listings_collection()

            where: dict = {}
            if area:
                where["area"] = area
            if listing_type:
                where["listing_type"] = listing_type

            query_params = {"query_texts": [query], "n_results": n_results}
            if where:
                query_params["where"] = where

            chroma_result = collection.query(**query_params)
            ids = chroma_result.get("ids", [[]])[0]
            distances = chroma_result.get("distances", [[]])[0]

        except Exception as e:
            return Response({"error": f"Vector search failed: {e}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not ids:
            return Response({"results": []})

        # Fetch from DB preserving order
        listings_map = {
            str(l.pk): l
            for l in MarketListing.objects.filter(pk__in=ids).select_related("agency").prefetch_related("photos")
        }
        results = []
        serializer_ctx = {"request": request}
        for listing_id, distance in zip(ids, distances):
            listing = listings_map.get(listing_id)
            if listing:
                data = MarketListingListSerializer(listing, context=serializer_ctx).data
                data["similarity_score"] = round(1 - float(distance), 4)
                results.append(data)

        return Response({"results": results, "query": query})


class MapExportView(APIView):
    """
    GET /api/v1/market-data/map-export/

    Returns a GeoJSON FeatureCollection of market listings suitable for
    plotting on Google Maps. Defaults to all Winelands areas, excluding
    cross-site duplicates (show canonical listings only).

    Query params:
        area            - AreaSlug (e.g. stellenbosch) — defaults to all winelands
        listing_type    - rent | sale
        min_price       - minimum price (rental or asking)
        max_price       - maximum price
        bedrooms        - exact bedroom count
        include_duplicates - 1 to include is_duplicate=True listings
    """
    permission_classes = [IsAuthenticated]
    MAP_FEATURE_CAP = 2000

    def get(self, request):
        area = request.query_params.get("area")
        listing_type = request.query_params.get("listing_type")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        bedrooms = request.query_params.get("bedrooms")
        include_duplicates = request.query_params.get("include_duplicates") == "1"

        qs = MarketListing.objects.filter(
            latitude__isnull=False, longitude__isnull=False
        ).select_related("agency").prefetch_related("photos")

        if area:
            qs = qs.filter(area=area)
        else:
            qs = qs.filter(area__in=[a.value for a in WINELANDS_AREAS])

        if not include_duplicates:
            qs = qs.filter(is_duplicate=False)

        if listing_type:
            qs = qs.filter(listing_type=listing_type)
        if bedrooms:
            qs = qs.filter(bedrooms=int(bedrooms))

        if min_price or max_price:
            # Filter against the active price field for the listing_type
            if listing_type == "rent":
                if min_price:
                    qs = qs.filter(rental_price__gte=min_price)
                if max_price:
                    qs = qs.filter(rental_price__lte=max_price)
            elif listing_type == "sale":
                if min_price:
                    qs = qs.filter(asking_price__gte=min_price)
                if max_price:
                    qs = qs.filter(asking_price__lte=max_price)
            else:
                # No listing_type — filter against either price field
                from django.db.models import Q
                if min_price:
                    qs = qs.filter(Q(rental_price__gte=min_price) | Q(asking_price__gte=min_price))
                if max_price:
                    qs = qs.filter(Q(rental_price__lte=max_price) | Q(asking_price__lte=max_price))

        features = []
        for listing in qs.order_by("-first_seen_at")[: self.MAP_FEATURE_CAP]:
            price = float(listing.rental_price or listing.asking_price or 0)
            cover = None
            first_photo = listing.photos.first()
            if first_photo:
                cover = (
                    request.build_absolute_uri(first_photo.photo_file.url)
                    if first_photo.photo_file
                    else first_photo.source_url
                )

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [listing.longitude, listing.latitude],
                },
                "properties": {
                    "id": listing.pk,
                    "source": listing.source,
                    "source_url": listing.source_url,
                    "listing_type": listing.listing_type,
                    "property_type": listing.property_type or "",
                    "ai_property_type": listing.ai_property_type,
                    "ai_condition": listing.ai_condition,
                    "ai_style": listing.ai_style,
                    "ai_confidence": listing.ai_classification_confidence,
                    "is_duplicate": listing.is_duplicate,
                    "area": listing.area,
                    "suburb": listing.suburb,
                    "bedrooms": listing.bedrooms,
                    "bathrooms": float(listing.bathrooms) if listing.bathrooms else None,
                    "floor_size_m2": float(listing.floor_size_m2) if listing.floor_size_m2 else None,
                    "price": price,
                    "price_currency": listing.price_currency,
                    "title": listing.title[:120],
                    "cover_photo": cover,
                    "agency": listing.agency.name if listing.agency else None,
                    "first_seen_at": listing.first_seen_at.isoformat() if listing.first_seen_at else None,
                },
            })

        return Response({
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        })

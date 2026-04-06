from django_filters import rest_framework as filters

from apps.market_data.models import AreaNewsArticle, AreaSlug, ListingType, MarketListing, MarketPriceStats, MunicipalBylaw, PropertyType, ScrapeRun, SourceSlug


class MarketListingFilter(filters.FilterSet):
    area           = filters.MultipleChoiceFilter(choices=AreaSlug.choices)
    source         = filters.MultipleChoiceFilter(choices=SourceSlug.choices)
    listing_type   = filters.ChoiceFilter(choices=ListingType.choices)
    property_type  = filters.MultipleChoiceFilter(choices=PropertyType.choices)
    bedrooms       = filters.NumberFilter()
    bedrooms__gte  = filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    bedrooms__lte  = filters.NumberFilter(field_name="bedrooms", lookup_expr="lte")
    min_price      = filters.NumberFilter(method="filter_min_price")
    max_price      = filters.NumberFilter(method="filter_max_price")
    suburb         = filters.CharFilter(lookup_expr="icontains")
    has_coords     = filters.BooleanFilter(method="filter_has_coords")
    enriched       = filters.BooleanFilter(method="filter_enriched")

    def filter_min_price(self, qs, name, value):
        return qs.filter(
            **{f"{self._price_field(qs)}__gte": value}
        )

    def filter_max_price(self, qs, name, value):
        return qs.filter(
            **{f"{self._price_field(qs)}__lte": value}
        )

    def _price_field(self, qs):
        listing_type = self.request.query_params.get("listing_type", "")
        return "rental_price" if listing_type == "rent" else "asking_price"

    def filter_has_coords(self, qs, name, value):
        if value:
            return qs.filter(latitude__isnull=False, longitude__isnull=False)
        return qs.filter(latitude__isnull=True)

    def filter_enriched(self, qs, name, value):
        if value:
            return qs.filter(enriched_at__isnull=False)
        return qs.filter(enriched_at__isnull=True)

    class Meta:
        model = MarketListing
        fields = ["area", "source", "listing_type", "property_type", "bedrooms"]


class MarketPriceStatsFilter(filters.FilterSet):
    area         = filters.ChoiceFilter(choices=AreaSlug.choices)
    listing_type = filters.ChoiceFilter(choices=ListingType.choices)
    property_type = filters.ChoiceFilter(choices=PropertyType.choices)
    bedrooms     = filters.NumberFilter()
    date_from    = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to      = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = MarketPriceStats
        fields = ["area", "listing_type", "property_type", "bedrooms"]


class ScrapeRunFilter(filters.FilterSet):
    source = filters.MultipleChoiceFilter(choices=SourceSlug.choices)
    area   = filters.MultipleChoiceFilter(choices=AreaSlug.choices)
    status = filters.MultipleChoiceFilter(choices=ScrapeRun.Status.choices)

    class Meta:
        model = ScrapeRun
        fields = ["source", "area", "status"]


class AreaNewsFilter(filters.FilterSet):
    area      = filters.CharFilter(method="filter_area")
    sentiment = filters.ChoiceFilter(choices=AreaNewsArticle.Sentiment.choices)
    topic     = filters.CharFilter(method="filter_topic")
    date_from = filters.DateTimeFilter(field_name="published_at", lookup_expr="gte")
    date_to   = filters.DateTimeFilter(field_name="published_at", lookup_expr="lte")
    source    = filters.CharFilter()

    def filter_area(self, qs, name, value):
        return qs.filter(areas_mentioned__contains=[value])

    def filter_topic(self, qs, name, value):
        return qs.filter(topics__contains=[value])

    class Meta:
        model = AreaNewsArticle
        fields = ["sentiment", "source"]


class MunicipalBylawFilter(filters.FilterSet):
    municipality = filters.ChoiceFilter(choices=MunicipalBylaw.Municipality.choices)
    category     = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = MunicipalBylaw
        fields = ["municipality", "category"]

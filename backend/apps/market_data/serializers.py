from rest_framework import serializers

from apps.market_data.models import (
    AreaNewsArticle,
    ListingAgency,
    ListingNearbyPlace,
    ListingStreetView,
    MarketListing,
    MarketListingPhoto,
    MarketPriceStats,
    MunicipalBylaw,
    ScrapeRun,
)


class ScrapeRunSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = ScrapeRun
        fields = "__all__"


class ListingAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingAgency
        fields = [
            "id", "source", "agent_type", "name", "agency_name",
            "phone", "profile_url", "photo_file", "agency_logo_file",
        ]


class MarketListingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketListingPhoto
        fields = ["id", "position", "source_url", "photo_file", "width_px", "height_px"]


class ListingStreetViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingStreetView
        fields = ["photo_file", "api_status", "fetched_at"]


class ListingNearbyPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingNearbyPlace
        fields = [
            "id", "name", "category", "place_type",
            "distance_m", "drive_minutes", "walk_minutes",
            "latitude", "longitude", "rating",
        ]


class MarketListingListSerializer(serializers.ModelSerializer):
    cover_photo = serializers.SerializerMethodField()
    agency = ListingAgencySerializer(read_only=True)

    class Meta:
        model = MarketListing
        fields = [
            "id", "source", "source_url", "listing_type", "property_type", "area",
            "agency", "asking_price", "rental_price", "sold_price",
            "bedrooms", "bathrooms", "floor_size_m2", "erf_size_m2", "parking",
            "is_furnished", "pets_allowed",
            "latitude", "longitude", "raw_address", "suburb", "city",
            "title", "cover_photo",
            "first_seen_at", "last_seen_at", "listed_at", "sold_at",
            "ai_property_type", "ai_condition", "is_duplicate",
        ]

    def get_cover_photo(self, obj):
        photo = obj.photos.filter(position=0).first() or obj.photos.first()
        if not photo:
            return None
        if photo.photo_file:
            request = self.context.get("request")
            return request.build_absolute_uri(photo.photo_file.url) if request else photo.photo_file.url
        return photo.source_url


class MarketListingDetailSerializer(MarketListingListSerializer):
    photos = MarketListingPhotoSerializer(many=True, read_only=True)
    street_view = ListingStreetViewSerializer(read_only=True)
    nearby_places = ListingNearbyPlaceSerializer(many=True, read_only=True)

    class Meta(MarketListingListSerializer.Meta):
        fields = MarketListingListSerializer.Meta.fields + [
            "source_listing_id", "description", "erf_size_m2", "previous_price", "price_changed_at",
            "photos", "street_view", "nearby_places", "enriched_at",
            # AI classification
            "ai_property_type", "ai_condition", "ai_style",
            "ai_classified_at", "ai_classification_confidence",
            # Deduplication
            "is_duplicate", "duplicate_score",
        ]


class MarketPriceStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketPriceStats
        fields = "__all__"


class AreaNewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaNewsArticle
        fields = [
            "id", "source", "title", "url", "published_at",
            "content_summary", "areas_mentioned", "topics", "sentiment",
        ]


class MunicipalBylawSerializer(serializers.ModelSerializer):
    class Meta:
        model = MunicipalBylaw
        fields = [
            "id", "municipality", "title", "category",
            "source_url", "document_file", "effective_date", "last_amended",
        ]

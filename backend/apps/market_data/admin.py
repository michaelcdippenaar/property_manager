from django.contrib import admin
from django.utils.html import format_html

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


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = [
        "source", "area", "listing_type", "status",
        "listings_found", "listings_saved", "listings_updated",
        "started_at", "duration_seconds",
    ]
    list_filter = ["source", "listing_type", "status"]
    search_fields = ["area", "error_message"]
    ordering = ["-started_at"]
    readonly_fields = ["started_at", "finished_at"]


class MarketListingPhotoInline(admin.TabularInline):
    model = MarketListingPhoto
    extra = 0
    fields = ["position", "photo_preview", "source_url", "is_downloaded", "width_px", "height_px"]
    readonly_fields = ["photo_preview", "is_downloaded", "downloaded_at", "width_px", "height_px"]

    def photo_preview(self, obj):
        src = obj.photo_file.url if obj.photo_file else obj.source_url
        if src:
            return format_html('<img src="{}" style="max-height:80px;max-width:120px;">', src)
        return "-"
    photo_preview.short_description = "Preview"


class ListingNearbyPlaceInline(admin.TabularInline):
    model = ListingNearbyPlace
    extra = 0
    fields = ["category", "name", "distance_m", "drive_minutes", "walk_minutes", "rating"]
    ordering = ["category", "distance_m"]


class ListingStreetViewInline(admin.StackedInline):
    model = ListingStreetView
    extra = 0
    fields = ["photo_preview", "api_status", "fetched_at"]
    readonly_fields = ["photo_preview", "fetched_at"]

    def photo_preview(self, obj):
        if obj.photo_file:
            return format_html('<img src="{}" style="max-width:320px;">', obj.photo_file.url)
        return f"Status: {obj.api_status}"
    photo_preview.short_description = "Street View"


@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = [
        "source", "area", "listing_type", "suburb",
        "bedrooms", "asking_price", "rental_price",
        "agency", "last_seen_at", "enriched_at",
    ]
    list_filter = ["source", "area", "listing_type", "property_type", "bedrooms"]
    search_fields = ["title", "raw_address", "suburb", "source_listing_id"]
    ordering = ["-last_seen_at"]
    readonly_fields = ["first_seen_at", "last_seen_at", "price_changed_at", "enriched_at"]
    inlines = [MarketListingPhotoInline, ListingStreetViewInline, ListingNearbyPlaceInline]
    list_select_related = ["agency"]
    raw_id_fields = ["agency", "scrape_run"]


@admin.register(ListingAgency)
class ListingAgencyAdmin(admin.ModelAdmin):
    list_display = ["name", "agency_name", "source", "agent_type", "phone", "listing_count"]
    list_filter = ["source", "agent_type"]
    search_fields = ["name", "agency_name", "phone", "email"]
    ordering = ["agency_name", "name"]

    def listing_count(self, obj):
        return obj.listings.count()
    listing_count.short_description = "Listings"


@admin.register(MarketPriceStats)
class MarketPriceStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date", "area", "listing_type", "property_type",
        "bedrooms", "sample_count", "avg_price", "median_price",
    ]
    list_filter = ["area", "listing_type", "property_type"]
    ordering = ["-date", "area"]


@admin.register(MunicipalBylaw)
class MunicipalBylawAdmin(admin.ModelAdmin):
    list_display = ["municipality", "category", "title", "effective_date", "last_amended", "vectorized"]
    list_filter = ["municipality", "category", "vectorized"]
    search_fields = ["title", "content_text"]
    ordering = ["municipality", "category", "title"]


@admin.register(AreaNewsArticle)
class AreaNewsArticleAdmin(admin.ModelAdmin):
    list_display = ["source", "title_truncated", "published_at", "sentiment", "areas_display", "vectorized"]
    list_filter = ["source", "sentiment", "vectorized"]
    search_fields = ["title", "content_summary"]
    ordering = ["-published_at"]

    def title_truncated(self, obj):
        return obj.title[:80]
    title_truncated.short_description = "Title"

    def areas_display(self, obj):
        return ", ".join(obj.areas_mentioned or [])
    areas_display.short_description = "Areas"

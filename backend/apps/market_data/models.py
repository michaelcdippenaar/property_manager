from __future__ import annotations

from django.db import models
from django.db.models import Avg, Max, Min
from django.utils import timezone


class AreaSlug(models.TextChoices):
    # Cape Peninsula
    CITY_BOWL            = "city_bowl",            "City Bowl"
    ATLANTIC_SEABOARD    = "atlantic_seaboard",    "Atlantic Seaboard"
    SOUTHERN_SUBURBS     = "southern_suburbs",     "Southern Suburbs"
    NORTHERN_SUBURBS_CPT = "northern_suburbs_cpt", "Northern Suburbs (Cape Town)"
    HELDERBERG           = "helderberg",            "Helderberg"
    FALSE_BAY            = "false_bay",             "False Bay"
    HOUT_BAY             = "hout_bay",              "Hout Bay"
    # Stellenbosch & Winelands
    STELLENBOSCH         = "stellenbosch",          "Stellenbosch"
    PAARL                = "paarl",                 "Paarl"
    FRANSCHHOEK          = "franschhoek",           "Franschhoek"
    SOMERSET_WEST        = "somerset_west",         "Somerset West"
    STRAND               = "strand",                "Strand"


CAPE_PENINSULA_AREAS = [
    AreaSlug.CITY_BOWL,
    AreaSlug.ATLANTIC_SEABOARD,
    AreaSlug.SOUTHERN_SUBURBS,
    AreaSlug.NORTHERN_SUBURBS_CPT,
    AreaSlug.HELDERBERG,
    AreaSlug.FALSE_BAY,
    AreaSlug.HOUT_BAY,
]

WINELANDS_AREAS = [
    AreaSlug.STELLENBOSCH,
    AreaSlug.PAARL,
    AreaSlug.FRANSCHHOEK,
    AreaSlug.SOMERSET_WEST,
    AreaSlug.STRAND,
]

ALL_AREAS = [a.value for a in AreaSlug]


class SourceSlug(models.TextChoices):
    PROPERTY24       = "property24",       "Property24"
    PRIVATE_PROPERTY = "private_property", "PrivateProperty"
    GUMTREE          = "gumtree",          "Gumtree"
    IOL_PROPERTY     = "iol_property",     "IOL Property"
    RENTFIND         = "rentfind",         "RentFind"
    PAM_GOLDING      = "pam_golding",      "Pam Golding"
    SEEFF            = "seeff",            "Seeff"
    FACEBOOK         = "facebook",         "Facebook"
    ANNA_BASSON      = "anna_basson",      "Anna Basson Eiendomme"
    ENGEL_VOLKERS    = "engel_volkers",    "Engel & Völkers"
    SOTHEBYS         = "sothebys",         "Sotheby's International Realty"
    CHAS_EVERITT     = "chas_everitt",     "Chas Everitt"
    LOUW_COETZEE     = "louw_coetzee",     "Louw & Coetzee"


class ListingType(models.TextChoices):
    RENT = "rent", "For Rent"
    SALE = "sale", "For Sale"


class PropertyType(models.TextChoices):
    APARTMENT  = "apartment",  "Apartment"
    HOUSE      = "house",      "House"
    TOWNHOUSE  = "townhouse",  "Townhouse"
    SIMPLEX    = "simplex",    "Simplex"
    DUPLEX     = "duplex",     "Duplex"
    STUDIO     = "studio",     "Studio"
    BACHELOR   = "bachelor",   "Bachelor"
    COMMERCIAL = "commercial", "Commercial"
    PLOT       = "plot",       "Plot / Land"
    FARM       = "farm",       "Farm / Wine Estate"
    OTHER      = "other",      "Other"


# ---------------------------------------------------------------------------
# ScrapeRun
# ---------------------------------------------------------------------------

class ScrapeRun(models.Model):
    class Status(models.TextChoices):
        RUNNING  = "running",  "Running"
        SUCCESS  = "success",  "Success"
        PARTIAL  = "partial",  "Partial (some errors)"
        FAILED   = "failed",   "Failed"

    source           = models.CharField(max_length=30, choices=SourceSlug.choices)
    area             = models.CharField(max_length=40, choices=AreaSlug.choices)
    listing_type     = models.CharField(max_length=10, choices=ListingType.choices)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at       = models.DateTimeField(auto_now_add=True)
    finished_at      = models.DateTimeField(null=True, blank=True)
    listings_found   = models.PositiveIntegerField(default=0)
    listings_saved   = models.PositiveIntegerField(default=0)
    listings_updated = models.PositiveIntegerField(default=0)
    listings_skipped = models.PositiveIntegerField(default=0)
    pages_scraped    = models.PositiveSmallIntegerField(default=0)
    error_message    = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["source", "area", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.source}/{self.area} [{self.status}] @ {self.started_at:%Y-%m-%d %H:%M}"

    def mark_done(self, status: str, error: str = ""):
        self.status = status
        self.finished_at = timezone.now()
        if error:
            self.error_message = error
        self.save(update_fields=["status", "finished_at", "error_message"])

    @property
    def duration_seconds(self):
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


# ---------------------------------------------------------------------------
# ListingAgency
# ---------------------------------------------------------------------------

class ListingAgency(models.Model):
    class AgentType(models.TextChoices):
        PERSON  = "person",  "Individual Agent"
        AGENCY  = "agency",  "Agency"
        PRIVATE = "private", "Private Seller"

    source          = models.CharField(max_length=30, choices=SourceSlug.choices)
    source_agent_id = models.CharField(max_length=100)
    agent_type      = models.CharField(max_length=10, choices=AgentType.choices, default=AgentType.AGENCY)
    name            = models.CharField(max_length=200)
    agency_name     = models.CharField(max_length=200, blank=True)
    phone           = models.CharField(max_length=30, blank=True)
    email           = models.CharField(max_length=200, blank=True)
    profile_url     = models.URLField(max_length=500, blank=True)
    photo_url       = models.URLField(max_length=500, blank=True)
    photo_file      = models.ImageField(upload_to="market_data/agents/", null=True, blank=True)
    agency_logo_url = models.URLField(max_length=500, blank=True)
    agency_logo_file = models.ImageField(upload_to="market_data/agencies/", null=True, blank=True)
    raw_data        = models.JSONField(default=dict, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("source", "source_agent_id")]
        verbose_name = "Listing Agency / Agent"
        verbose_name_plural = "Listing Agencies / Agents"

    def __str__(self):
        if self.agency_name:
            return f"{self.name} @ {self.agency_name} ({self.source})"
        return f"{self.name} ({self.source})"


# ---------------------------------------------------------------------------
# MarketListing
# ---------------------------------------------------------------------------

class MarketListing(models.Model):
    # Identity / deduplication
    source            = models.CharField(max_length=30, choices=SourceSlug.choices, db_index=True)
    source_listing_id = models.CharField(max_length=100)
    source_url        = models.URLField(max_length=500)

    # Classification
    listing_type  = models.CharField(max_length=10, choices=ListingType.choices, db_index=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True)
    area          = models.CharField(max_length=40, choices=AreaSlug.choices, db_index=True)

    # Agency relation
    agency = models.ForeignKey(
        ListingAgency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
    )

    # Pricing
    asking_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    sold_price      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    rental_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    previous_price  = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    price_changed_at = models.DateTimeField(null=True, blank=True)
    price_currency  = models.CharField(max_length=3, default="ZAR")

    # Property attributes
    bedrooms    = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms   = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    floor_size_m2 = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    erf_size_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parking     = models.PositiveSmallIntegerField(null=True, blank=True)
    is_furnished = models.BooleanField(null=True, blank=True)
    pets_allowed = models.BooleanField(null=True, blank=True)

    # Location — coordinates are primary; raw_address is fallback
    latitude    = models.FloatField(null=True, blank=True, db_index=True)
    longitude   = models.FloatField(null=True, blank=True)
    raw_address = models.TextField(blank=True)
    suburb      = models.CharField(max_length=100, blank=True)
    city        = models.CharField(max_length=100, blank=True)
    province    = models.CharField(max_length=100, default="Western Cape")

    # Content
    title       = models.TextField(blank=True)
    description = models.TextField(blank=True)

    # Timestamps
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at  = models.DateTimeField(auto_now=True)
    listed_at     = models.DateTimeField(null=True, blank=True)
    sold_at       = models.DateTimeField(null=True, blank=True)

    # Enrichment flags
    enriched_at = models.DateTimeField(null=True, blank=True)

    # AI visual classification (from street view + Claude Vision)
    ai_property_type             = models.CharField(max_length=30, blank=True)
    ai_condition                 = models.CharField(max_length=20, blank=True)
    ai_style                     = models.CharField(max_length=30, blank=True)
    ai_classified_at             = models.DateTimeField(null=True, blank=True)
    ai_classification_confidence = models.FloatField(null=True, blank=True)

    # Cross-site deduplication
    canonical_listing = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="duplicates",
    )
    is_duplicate    = models.BooleanField(default=False, db_index=True)
    duplicate_score = models.FloatField(null=True, blank=True)

    # Scrape metadata
    scrape_run = models.ForeignKey(
        ScrapeRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
    )
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("source", "source_listing_id")]
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["area", "listing_type", "bedrooms", "asking_price"]),
            models.Index(fields=["area", "listing_type", "bedrooms", "rental_price"]),
            models.Index(fields=["source", "area", "-last_seen_at"]),
            models.Index(fields=["listing_type", "property_type", "area"]),
            models.Index(fields=["agency", "listing_type"]),
        ]

    def __str__(self):
        price = self.rental_price or self.asking_price
        return f"[{self.source}] {self.title[:60] or self.suburb} — R{price}"

    @property
    def active_price(self):
        return self.rental_price if self.listing_type == ListingType.RENT else self.asking_price


# ---------------------------------------------------------------------------
# MarketListingPhoto
# ---------------------------------------------------------------------------

class MarketListingPhoto(models.Model):
    listing      = models.ForeignKey(MarketListing, on_delete=models.CASCADE, related_name="photos")
    position     = models.PositiveSmallIntegerField(default=0)
    source_url   = models.URLField(max_length=500)
    photo_file   = models.ImageField(upload_to="market_data/listings/photos/", null=True, blank=True)
    is_downloaded = models.BooleanField(default=False)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    width_px     = models.PositiveSmallIntegerField(null=True, blank=True)
    height_px    = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["listing", "position"]

    def __str__(self):
        return f"Photo {self.position} for listing {self.listing_id}"


# ---------------------------------------------------------------------------
# ListingStreetView
# ---------------------------------------------------------------------------

class ListingStreetView(models.Model):
    class ApiStatus(models.TextChoices):
        OK             = "OK",             "OK"
        ZERO_RESULTS   = "ZERO_RESULTS",   "Zero Results"
        NOT_FOUND      = "NOT_FOUND",      "Not Found"
        QUOTA_EXCEEDED = "QUOTA_EXCEEDED", "Quota Exceeded"
        ERROR          = "ERROR",          "Error"

    listing    = models.OneToOneField(MarketListing, on_delete=models.CASCADE, related_name="street_view")
    photo_file = models.ImageField(upload_to="market_data/streetview/", null=True, blank=True)
    heading    = models.FloatField(default=0.0)
    pitch      = models.FloatField(default=0.0)
    fov        = models.PositiveSmallIntegerField(default=90)
    fetched_at = models.DateTimeField(auto_now_add=True)
    api_status = models.CharField(max_length=20, choices=ApiStatus.choices, default=ApiStatus.OK)

    def __str__(self):
        return f"StreetView for listing {self.listing_id} [{self.api_status}]"


# ---------------------------------------------------------------------------
# ListingNearbyPlace
# ---------------------------------------------------------------------------

class ListingNearbyPlace(models.Model):
    CATEGORY_CHOICES = [
        ("school",       "School / University"),
        ("supermarket",  "Supermarket / Shopping"),
        ("hospital",     "Hospital / Medical"),
        ("gym",          "Gym / Park / Recreation"),
        ("transit",      "Public Transport"),
        ("restaurant",   "Restaurant / Cafe"),
        ("winery",       "Winery / Tourist Attraction"),
        ("beach",        "Beach / Nature"),
        ("other",        "Other"),
    ]

    listing      = models.ForeignKey(MarketListing, on_delete=models.CASCADE, related_name="nearby_places")
    place_id     = models.CharField(max_length=100)
    name         = models.CharField(max_length=200)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    place_type   = models.CharField(max_length=100, blank=True)
    distance_m   = models.PositiveIntegerField(null=True, blank=True)
    drive_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    walk_minutes  = models.PositiveSmallIntegerField(null=True, blank=True)
    latitude     = models.FloatField(null=True, blank=True)
    longitude    = models.FloatField(null=True, blank=True)
    rating       = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    fetched_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("listing", "place_id")]
        ordering = ["listing", "category", "distance_m"]

    def __str__(self):
        return f"{self.name} ({self.category}) — {self.distance_m}m from listing {self.listing_id}"


# ---------------------------------------------------------------------------
# MarketPriceStats
# ---------------------------------------------------------------------------

class MarketPriceStats(models.Model):
    date         = models.DateField(db_index=True)
    area         = models.CharField(max_length=40, choices=AreaSlug.choices)
    listing_type = models.CharField(max_length=10, choices=ListingType.choices)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True)
    bedrooms     = models.PositiveSmallIntegerField(null=True, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    avg_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    median_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    min_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    avg_price_per_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("date", "area", "listing_type", "property_type", "bedrooms")]
        ordering = ["-date", "area"]

    def __str__(self):
        return f"{self.date} | {self.area} | {self.listing_type} | {self.bedrooms}br | avg R{self.avg_price}"

    @classmethod
    def refresh_for_date(cls, date):
        from django.db.models import Percentile
        price_field_map = {
            ListingType.RENT: "rental_price",
            ListingType.SALE: "asking_price",
        }
        for listing_type, price_field in price_field_map.items():
            qs = MarketListing.objects.filter(
                listing_type=listing_type,
                last_seen_at__date=date,
            ).exclude(**{f"{price_field}__isnull": True})

            for area in AreaSlug:
                area_qs = qs.filter(area=area.value)
                if not area_qs.exists():
                    continue
                for prop_type_val in [""] + [p.value for p in PropertyType]:
                    type_qs = area_qs.filter(property_type=prop_type_val) if prop_type_val else area_qs
                    for bedroom_val in [None] + list(range(0, 8)):
                        if bedroom_val is None:
                            bed_qs = type_qs
                        else:
                            bed_qs = type_qs.filter(bedrooms=bedroom_val)
                        if not bed_qs.exists():
                            continue
                        prices = list(bed_qs.values_list(price_field, flat=True).order_by(price_field))
                        count = len(prices)
                        agg = bed_qs.aggregate(
                            avg=Avg(price_field),
                            min=Min(price_field),
                            max=Max(price_field),
                        )
                        mid = count // 2
                        median = prices[mid] if count % 2 == 1 else (prices[mid - 1] + prices[mid]) / 2

                        # price per m2
                        m2_qs = bed_qs.exclude(floor_size_m2__isnull=True).exclude(floor_size_m2=0)
                        avg_per_m2 = None
                        if m2_qs.exists():
                            total = sum(
                                float(p) / float(s)
                                for p, s in m2_qs.values_list(price_field, "floor_size_m2")
                            )
                            avg_per_m2 = round(total / m2_qs.count(), 2)

                        cls.objects.update_or_create(
                            date=date,
                            area=area.value,
                            listing_type=listing_type,
                            property_type=prop_type_val,
                            bedrooms=bedroom_val,
                            defaults={
                                "sample_count": count,
                                "avg_price": agg["avg"],
                                "median_price": median,
                                "min_price": agg["min"],
                                "max_price": agg["max"],
                                "avg_price_per_m2": avg_per_m2,
                            },
                        )


# ---------------------------------------------------------------------------
# MunicipalBylaw
# ---------------------------------------------------------------------------

class MunicipalBylaw(models.Model):
    class Municipality(models.TextChoices):
        CITY_OF_CAPE_TOWN = "city_of_cape_town", "City of Cape Town"
        STELLENBOSCH      = "stellenbosch",      "Stellenbosch Municipality"
        DRAKENSTEIN       = "drakenstein",        "Drakenstein Municipality"

    municipality  = models.CharField(max_length=30, choices=Municipality.choices)
    title         = models.CharField(max_length=300)
    category      = models.CharField(max_length=100, blank=True)
    source_url    = models.URLField(max_length=500)
    document_file = models.FileField(upload_to="market_data/bylaws/", null=True, blank=True)
    content_text  = models.TextField(blank=True)
    effective_date = models.DateField(null=True, blank=True)
    last_amended  = models.DateField(null=True, blank=True)
    scraped_at    = models.DateTimeField(auto_now_add=True)
    vectorized    = models.BooleanField(default=False)

    class Meta:
        ordering = ["municipality", "category", "title"]

    def __str__(self):
        return f"[{self.municipality}] {self.title}"


# ---------------------------------------------------------------------------
# AreaNewsArticle
# ---------------------------------------------------------------------------

class AreaNewsArticle(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL  = "neutral",  "Neutral"
        NEGATIVE = "negative", "Negative"

    source            = models.CharField(max_length=50)
    source_article_id = models.CharField(max_length=200, unique=True)
    title             = models.TextField()
    url               = models.URLField(max_length=500)
    published_at      = models.DateTimeField(null=True, blank=True)
    content_summary   = models.TextField(blank=True)
    areas_mentioned   = models.JSONField(default=list, blank=True)
    topics            = models.JSONField(default=list, blank=True)
    sentiment         = models.CharField(
        max_length=10, choices=Sentiment.choices, default=Sentiment.NEUTRAL
    )
    vectorized        = models.BooleanField(default=False)
    scraped_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["sentiment", "-published_at"]),
        ]

    def __str__(self):
        return f"[{self.source}] {self.title[:80]}"

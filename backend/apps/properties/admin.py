from django.contrib import admin
from django.utils.html import format_html

from .models import (
    BankAccount,
    ComplianceCertificate,
    InsuranceClaim,
    InsurancePolicy,
    Landlord,
    MunicipalAccount,
    MunicipalBill,
    Property,
    PropertyDetail,
    PropertyGroup,
    PropertyOwnership,
    PropertyPhoto,
    PropertyValuation,
    Unit,
    UnitInfo,
)


class PropertyDetailInline(admin.StackedInline):
    model = PropertyDetail
    extra = 0
    fieldsets = (
        ("Legal / Deeds", {
            "fields": ("erf_number", "title_deed_number", "municipality", "suburb", "zoning"),
        }),
        ("Dimensions", {
            "fields": ("erf_size_m2", "floor_size_m2", "latitude", "longitude"),
        }),
        ("Construction", {
            "fields": ("year_built", "construction_type", "roof_type", "number_of_storeys",
                       "has_garage", "has_pool", "has_flatlet", "garden_type"),
        }),
        ("Financial", {
            "fields": ("purchase_price", "purchase_date", "current_valuation", "valuation_date",
                       "municipal_value", "municipal_value_date"),
        }),
        ("Google Drive", {
            "fields": ("drive_photos_url", "drive_documents_url", "drive_plans_url"),
            "classes": ("collapse",),
        }),
        ("Notes", {"fields": ("notes",)}),
    )


class PropertyPhotoInline(admin.TabularInline):
    model = PropertyPhoto
    extra = 0
    fields = ("photo", "category", "caption", "position", "is_cover", "drive_url")
    readonly_fields = ("uploaded_at",)


class ComplianceCertInline(admin.TabularInline):
    model = ComplianceCertificate
    extra = 0
    fields = ("cert_type", "certificate_number", "issued_date", "expiry_date",
              "contractor_name", "document", "cert_status")
    readonly_fields = ("cert_status",)

    @admin.display(description="Status")
    def cert_status(self, obj):
        status = obj.get_status()
        colour = "green" if status == "valid" else "red"
        return format_html('<span style="color:{}">{}</span>', colour, status.upper())


class MunicipalAccountInline(admin.TabularInline):
    model = MunicipalAccount
    extra = 0
    fields = ("account_type", "account_number", "municipality", "reference",
              "meter_number", "monthly_levy", "in_tenant_name")


class PropertyValuationInline(admin.TabularInline):
    model = PropertyValuation
    extra = 0
    fields = ("valuation_type", "amount", "valuation_date", "valuator")


class UnitInline(admin.TabularInline):
    model = Unit
    extra = 0
    fields = ("unit_number", "bedrooms", "bathrooms", "rent_amount", "status", "floor")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "property_type", "city", "erf_number_display", "created_at")
    list_filter = ("property_type", "city")
    search_fields = ("name", "address", "detail__erf_number")
    inlines = [
        PropertyDetailInline,
        UnitInline,
        PropertyPhotoInline,
        ComplianceCertInline,
        MunicipalAccountInline,
        PropertyValuationInline,
    ]

    @admin.display(description="ERF")
    def erf_number_display(self, obj):
        try:
            return obj.detail.erf_number
        except PropertyDetail.DoesNotExist:
            return "—"


@admin.register(ComplianceCertificate)
class ComplianceCertificateAdmin(admin.ModelAdmin):
    list_display = ("property", "cert_type", "certificate_number", "issued_date", "expiry_date", "cert_status", "contractor_name")
    list_filter = ("cert_type",)
    search_fields = ("property__name", "certificate_number", "contractor_name")

    @admin.display(description="Status")
    def cert_status(self, obj):
        status = obj.get_status()
        colour = "green" if status == "valid" else "red"
        return format_html('<span style="color:{}">{}</span>', colour, status.upper())


@admin.register(MunicipalAccount)
class MunicipalAccountAdmin(admin.ModelAdmin):
    list_display = ("property", "account_type", "account_number", "municipality", "monthly_levy", "in_tenant_name")
    list_filter = ("account_type", "in_tenant_name")
    search_fields = ("property__name", "account_number", "reference")


@admin.register(PropertyValuation)
class PropertyValuationAdmin(admin.ModelAdmin):
    list_display = ("property", "valuation_type", "amount", "valuation_date", "valuator")
    list_filter = ("valuation_type",)
    search_fields = ("property__name",)


@admin.register(Landlord)
class LandlordAdmin(admin.ModelAdmin):
    list_display = ("name", "landlord_type", "email", "phone")
    list_filter = ("landlord_type",)
    search_fields = ("name", "email", "id_number")
    inlines = [
        type("BankAccountInline", (admin.TabularInline,), {
            "model": BankAccount,
            "extra": 0,
            "fields": ("label", "bank_name", "branch_code", "account_number", "account_type", "account_holder", "is_default"),
        })
    ]


@admin.register(PropertyGroup)
class PropertyGroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    filter_horizontal = ("properties",)


@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(admin.ModelAdmin):
    list_display = ("property", "owner_name", "owner_type", "start_date", "end_date", "is_current")
    list_filter = ("owner_type", "is_current")
    search_fields = ("property__name", "owner_name")


class InsuranceClaimInline(admin.TabularInline):
    model = InsuranceClaim
    extra = 0
    fields = ("claim_type", "claim_number", "status", "incident_date", "claimed_amount", "settlement_amount", "settled_date")


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ("property", "insurer", "policy_type", "policy_number", "monthly_premium", "sum_insured", "start_date", "is_active")
    list_filter = ("policy_type", "is_active", "insurer")
    search_fields = ("property__name", "policy_number", "insurer")
    inlines = [InsuranceClaimInline]


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ("property", "claim_type", "claim_number", "status", "incident_date", "claimed_amount", "settlement_amount")
    list_filter = ("claim_type", "status")
    search_fields = ("property__name", "claim_number", "description")
    date_hierarchy = "incident_date"


@admin.register(MunicipalBill)
class MunicipalBillAdmin(admin.ModelAdmin):
    list_display = ("property", "billing_year", "billing_month", "total_amount", "payment_status", "due_date", "paid_date")
    list_filter = ("payment_status", "billing_year")
    search_fields = ("property__name", "account_number", "payment_reference")
    date_hierarchy = "due_date"

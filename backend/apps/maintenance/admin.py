from django.contrib import admin
from .models import (
    JobDispatch, JobQuote, JobQuoteRequest,
    MaintenanceRequest, Supplier, SupplierDocument,
    SupplierProperty, SupplierTrade,
)


class SupplierTradeInline(admin.TabularInline):
    model = SupplierTrade
    extra = 1


class SupplierDocumentInline(admin.TabularInline):
    model = SupplierDocument
    extra = 0


class SupplierPropertyInline(admin.TabularInline):
    model = SupplierProperty
    extra = 0
    raw_id_fields = ["property"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "company_name", "phone", "city", "is_active", "rating"]
    list_filter = ["is_active", "city"]
    search_fields = ["name", "company_name", "phone", "email"]
    inlines = [SupplierTradeInline, SupplierDocumentInline, SupplierPropertyInline]


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ["title", "unit", "tenant", "supplier", "priority", "status", "created_at"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "description"]


class JobQuoteRequestInline(admin.TabularInline):
    model = JobQuoteRequest
    extra = 0
    readonly_fields = ["token", "notified_at", "viewed_at", "match_score"]


@admin.register(JobDispatch)
class JobDispatchAdmin(admin.ModelAdmin):
    list_display = ["maintenance_request", "status", "dispatched_by", "dispatched_at"]
    list_filter = ["status"]
    inlines = [JobQuoteRequestInline]


@admin.register(JobQuote)
class JobQuoteAdmin(admin.ModelAdmin):
    list_display = ["quote_request", "amount", "estimated_days", "submitted_at"]

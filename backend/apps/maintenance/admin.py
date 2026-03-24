from django.contrib import admin
from .models import MaintenanceRequest, Supplier, SupplierTrade


class SupplierTradeInline(admin.TabularInline):
    model = SupplierTrade
    extra = 1


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "company_name", "phone", "city", "is_active", "rating"]
    list_filter = ["is_active", "city"]
    search_fields = ["name", "company_name", "phone", "email"]
    inlines = [SupplierTradeInline]


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ["title", "unit", "tenant", "supplier", "priority", "status", "created_at"]
    list_filter = ["status", "priority"]
    search_fields = ["title", "description"]

from django.contrib import admin
from .models import (
    AgencySLAConfig,
    AgentQuestion, AgentTokenLog, JobDispatch, JobQuote, JobQuoteRequest,
    MaintenanceActivity, MaintenanceRequest, MaintenanceSkill,
    Supplier, SupplierDocument, SupplierJobAssignment, SupplierProperty, SupplierTrade,
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


@admin.register(AgentQuestion)
class AgentQuestionAdmin(admin.ModelAdmin):
    list_display = ["question_short", "category", "status", "added_to_context", "answered_by", "created_at"]
    list_filter = ["status", "category", "added_to_context"]
    search_fields = ["question", "answer"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["property", "answered_by"]

    @admin.display(description="Question")
    def question_short(self, obj):
        return obj.question[:80]


@admin.register(MaintenanceSkill)
class MaintenanceSkillAdmin(admin.ModelAdmin):
    list_display = ["name", "trade", "difficulty", "is_active", "updated_at"]
    list_filter = ["trade", "difficulty", "is_active"]
    search_fields = ["name", "notes"]


@admin.register(MaintenanceActivity)
class MaintenanceActivityAdmin(admin.ModelAdmin):
    list_display = ["request", "activity_type", "message_short", "created_by", "created_at"]
    list_filter = ["activity_type"]
    search_fields = ["message"]
    raw_id_fields = ["request", "created_by"]
    readonly_fields = ["created_at"]

    @admin.display(description="Message")
    def message_short(self, obj):
        return obj.message[:100] if obj.message else ""


@admin.register(AgentTokenLog)
class AgentTokenLogAdmin(admin.ModelAdmin):
    list_display = ["endpoint", "model", "input_tokens", "output_tokens", "latency_ms", "user", "created_at"]
    list_filter = ["endpoint", "model"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["user"]


@admin.register(AgencySLAConfig)
class AgencySLAConfigAdmin(admin.ModelAdmin):
    list_display = ["agency", "priority", "ack_hours", "resolve_hours"]
    list_filter = ["priority"]
    raw_id_fields = ["agency"]


@admin.register(SupplierJobAssignment)
class SupplierJobAssignmentAdmin(admin.ModelAdmin):
    list_display = ["supplier", "maintenance_request", "status", "property_address", "created_at"]
    list_filter = ["status"]
    search_fields = ["supplier__email", "property_address", "scope_of_work"]
    raw_id_fields = ["supplier", "maintenance_request", "assigned_by"]

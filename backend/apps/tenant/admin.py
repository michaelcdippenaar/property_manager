from django.contrib import admin
from django.utils.html import format_html

from .models import Tenant, TenantOnboarding, TenantUnitAssignment


class TenantUnitAssignmentInline(admin.TabularInline):
    model = TenantUnitAssignment
    extra = 0
    fields = (
        "unit",
        "property",
        "start_date",
        "end_date",
        "source",
        "assigned_by",
        "lease",
        "notes",
        "created_at",
    )
    readonly_fields = ("source", "lease", "property", "created_at")
    ordering = ("-start_date",)
    show_change_link = True

    def get_extra(self, request, obj=None, **kwargs):
        # Only show an empty row when creating a new tenant
        return 1 if obj is None else 0


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "person_name",
        "current_unit_display",
        "current_property_display",
        "is_active",
        "linked_user",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "person__full_name",
        "person__email",
        "person__id_number",
        "linked_user__email",
    )
    raw_id_fields = ("person", "linked_user")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TenantUnitAssignmentInline]
    fieldsets = (
        (
            None,
            {
                "fields": ("person", "linked_user", "is_active"),
            },
        ),
        (
            "Notes",
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Tenant Name", ordering="person__full_name")
    def person_name(self, obj: Tenant) -> str:
        return obj.person.full_name

    @admin.display(description="Current Unit")
    def current_unit_display(self, obj: Tenant):
        assignment = obj.current_assignment
        if assignment:
            return str(assignment.unit)
        return format_html('<span style="color:#9ca3af;">—</span>')

    @admin.display(description="Current Property")
    def current_property_display(self, obj: Tenant):
        assignment = obj.current_assignment
        if assignment:
            return str(assignment.property)
        return format_html('<span style="color:#9ca3af;">—</span>')


@admin.register(TenantOnboarding)
class TenantOnboardingAdmin(admin.ModelAdmin):
    list_display = (
        "lease",
        "progress_display",
        "welcome_pack_sent",
        "deposit_received",
        "first_rent_scheduled",
        "keys_handed_over",
        "emergency_contacts_captured",
        "completed_at",
    )
    list_filter = (
        "welcome_pack_sent",
        "deposit_received",
        "keys_handed_over",
        "emergency_contacts_captured",
    )
    search_fields = (
        "lease__lease_number",
        "lease__primary_tenant__full_name",
    )
    raw_id_fields = ("lease",)
    readonly_fields = (
        "welcome_pack_sent_at",
        "deposit_received_at",
        "first_rent_scheduled_at",
        "keys_handed_over_at",
        "emergency_contacts_captured_at",
        "incoming_inspection_booked_at",
        "deposit_banked_trust_at",
        "completed_at",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Progress")
    def progress_display(self, obj: TenantOnboarding) -> str:
        return f"{obj.progress}%"


@admin.register(TenantUnitAssignment)
class TenantUnitAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "unit",
        "property",
        "start_date",
        "end_date",
        "source",
        "assigned_by",
        "created_at",
    )
    list_filter = ("source", "property", "unit__property")
    search_fields = (
        "tenant__person__full_name",
        "tenant__person__email",
        "unit__unit_number",
        "property__name",
    )
    raw_id_fields = ("tenant", "unit", "property", "lease", "assigned_by")
    readonly_fields = ("source", "lease", "property", "created_at")
    date_hierarchy = "start_date"
    ordering = ("-start_date",)

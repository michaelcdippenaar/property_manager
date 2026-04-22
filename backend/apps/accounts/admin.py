from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Person, Agency, UserInvite, AuthAuditLog, LoginAttempt, UserTOTP, TOTPRecoveryCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "role", "agency", "is_active", "date_joined")
    list_filter = ("role", "agency", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone", "id_number")}),
        ("Role & Agency", {"fields": ("role", "agency", "module_access", "ffc_number", "ffc_category")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "role", "agency")}),
    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name", "person_type", "email", "phone", "linked_user")
    list_filter = ("person_type",)
    search_fields = ("full_name", "email", "phone", "id_number")


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "email", "eaab_ffc_number", "is_active")
    list_filter = ("account_type", "is_active")
    search_fields = ("name", "trading_name", "registration_number")


@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "invited_by", "created_at", "accepted_at", "cancelled_at")
    list_filter = ("role",)
    search_fields = ("email",)
    readonly_fields = ("token",)


@admin.register(AuthAuditLog)
class AuthAuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "ip_address", "created_at")
    list_filter = ("event_type",)
    search_fields = ("user__email", "ip_address")
    readonly_fields = ("user", "event_type", "ip_address", "user_agent", "metadata", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("email", "ip_address", "succeeded", "created_at")
    list_filter = ("succeeded",)
    search_fields = ("email", "ip_address")
    readonly_fields = ("email", "ip_address", "succeeded", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserTOTP)
class UserTOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "enrolled_at", "grace_deadline", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "secret", "enrolled_at", "grace_deadline", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(TOTPRecoveryCode)
class TOTPRecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "code_hash", "used_at", "created_at")

    def has_add_permission(self, request):
        return False

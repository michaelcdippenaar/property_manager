from django.contrib import admin, messages

from apps.the_volt.owners.models import VaultOwner, VaultOwnerAPIKey
from apps.the_volt.entities.models import VaultEntity, EntityRelationship, RelationshipTypeCatalogue  # noqa: F401
from apps.the_volt.documents.models import (
    VaultDocument,
    DocumentVersion,
    DocumentVerification,
    DocumentTypeCatalogue,
)
from apps.the_volt.entities.models import EntityDataField
from apps.the_volt.gateway.models import (
    DataSubscriber,
    DataRequest,
    DataRequestApprovalLink,
    DataCheckout,
    VaultWriteAudit,
)
from apps.the_volt.schemas.models import EntitySchema


@admin.register(VaultOwner)
class VaultOwnerAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    raw_id_fields = ["user"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]


@admin.register(VaultEntity)
class VaultEntityAdmin(admin.ModelAdmin):
    list_display = ["name", "entity_type", "vault", "is_active", "created_at"]
    list_filter = ["entity_type", "is_active"]
    search_fields = ["name"]
    raw_id_fields = ["vault"]
    readonly_fields = ["chroma_id", "created_at", "updated_at"]


@admin.register(EntityRelationship)
class EntityRelationshipAdmin(admin.ModelAdmin):
    list_display = ["from_entity", "relationship_type", "to_entity", "created_at"]
    list_filter = ["relationship_type"]
    raw_id_fields = ["vault", "from_entity", "to_entity"]


@admin.register(VaultDocument)
class VaultDocumentAdmin(admin.ModelAdmin):
    list_display = ["label", "document_type", "entity", "created_at"]
    list_filter = ["document_type"]
    raw_id_fields = ["entity", "current_version"]
    search_fields = ["label", "entity__name"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "original_filename", "file_size_bytes", "uploaded_at"]
    list_filter = ["document__document_type"]
    raw_id_fields = ["document"]
    readonly_fields = ["sha256_hash", "chroma_id", "uploaded_at"]


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = [
        "document_version", "verification_status", "verified_at",
        "commissioner_name", "expiry_date",
    ]
    list_filter = ["verification_status"]
    raw_id_fields = ["document_version"]
    readonly_fields = [
        "certified_copy_sha256", "certified_copy_original_filename",
        "created_at", "updated_at",
    ]


@admin.register(EntityDataField)
class EntityDataFieldAdmin(admin.ModelAdmin):
    list_display = [
        "entity", "field_key", "verification_status",
        "extraction_source", "verified_at", "expiry_date",
    ]
    list_filter = ["verification_status", "extraction_source"]
    raw_id_fields = ["entity", "source_document_version"]
    search_fields = ["field_key", "entity__name"]
    readonly_fields = ["chroma_id", "created_at", "updated_at"]


@admin.register(DataSubscriber)
class DataSubscriberAdmin(admin.ModelAdmin):
    list_display = ["org_name", "org_contact_email", "api_key_prefix", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["org_name", "org_contact_email"]
    readonly_fields = ["api_key_hash", "created_at"]


@admin.register(DataRequest)
class DataRequestAdmin(admin.ModelAdmin):
    list_display = ["subscriber", "vault", "status", "created_at", "expires_at"]
    list_filter = ["status"]
    raw_id_fields = ["subscriber", "vault", "approved_by"]
    readonly_fields = ["access_token", "created_at"]


@admin.register(DataRequestApprovalLink)
class DataRequestApprovalLinkAdmin(admin.ModelAdmin):
    list_display = ["token", "request", "otp_attempts", "expires_at", "used_at"]
    raw_id_fields = ["request"]
    readonly_fields = ["token", "otp_hash", "created_at"]


@admin.register(DataCheckout)
class DataCheckoutAdmin(admin.ModelAdmin):
    list_display = ["checkout_token", "request", "delivery_method", "authorisation_method", "checked_out_at"]
    list_filter = ["delivery_method", "authorisation_method"]
    raw_id_fields = ["request"]
    readonly_fields = [
        "checkout_token", "entities_shared", "documents_shared",
        "data_hash", "package_signature", "checked_out_at",
    ]


@admin.register(RelationshipTypeCatalogue)
class RelationshipTypeCatalogueAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "inverse_label", "is_system", "is_active", "sort_order"]
    list_filter = ["is_system", "is_active"]
    search_fields = ["code", "label", "regulatory_reference"]
    readonly_fields = ["is_system", "created_at", "updated_at"]


@admin.register(DocumentTypeCatalogue)
class DocumentTypeCatalogueAdmin(admin.ModelAdmin):
    list_display = [
        "code", "label", "issuing_authority", "ownership_scope",
        "is_primary_identity_doc", "is_active", "sort_order",
    ]
    list_filter = ["ownership_scope", "issuing_authority", "is_primary_identity_doc", "is_active"]
    search_fields = ["code", "label", "regulatory_reference"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(VaultOwnerAPIKey)
class VaultOwnerAPIKeyAdmin(admin.ModelAdmin):
    list_display = ["label", "vault_owner", "api_key_prefix", "is_active", "last_used_at", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["label", "vault_owner__user__email"]
    raw_id_fields = ["vault_owner"]
    readonly_fields = ["api_key_hash", "api_key_prefix", "last_used_at", "revoked_at", "created_at"]
    actions = ["generate_new_key", "revoke_selected"]

    @admin.action(description="Generate new API key for selected owner (creates new row)")
    def generate_new_key(self, request, queryset):
        for existing in queryset:
            key, raw = VaultOwnerAPIKey.create_for_owner(
                existing.vault_owner,
                label=f"Regenerated from {existing.label}",
            )
            self.message_user(
                request,
                f"New key for {existing.vault_owner}: {raw} — SAVE THIS NOW, it will not be shown again.",
                level=messages.WARNING,
            )

    @admin.action(description="Revoke selected keys")
    def revoke_selected(self, request, queryset):
        for key in queryset.filter(is_active=True):
            key.revoke()
        self.message_user(request, f"Revoked {queryset.count()} key(s).")


@admin.register(VaultWriteAudit)
class VaultWriteAuditAdmin(admin.ModelAdmin):
    list_display = ["operation", "target_model", "target_id", "vault", "api_key", "created_at"]
    list_filter = ["operation", "target_model"]
    search_fields = ["vault__user__email", "target_model"]
    raw_id_fields = ["vault", "api_key"]
    readonly_fields = [
        "vault", "api_key", "operation", "target_model", "target_id",
        "before", "after", "client_info", "created_at",
    ]

    def has_add_permission(self, request):
        return False  # Audit is append-only via code path

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EntitySchema)
class EntitySchemaAdmin(admin.ModelAdmin):
    list_display = ["entity_type", "country_code", "version", "label", "is_active", "created_at"]
    list_filter = ["entity_type", "country_code", "is_active"]
    search_fields = ["label"]
    readonly_fields = ["created_at", "updated_at"]

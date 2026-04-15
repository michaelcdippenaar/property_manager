from django.db import models

from apps.the_volt.owners.models import VaultOwner


class EntityType(models.TextChoices):
    PERSONAL = "personal", "Personal"
    TRUST = "trust", "Trust"
    COMPANY = "company", "Company"
    CLOSE_CORPORATION = "close_corporation", "Close Corporation"
    SOLE_PROPRIETARY = "sole_proprietary", "Sole Proprietary"
    ASSET = "asset", "Asset"


class RelationshipType(models.TextChoices):
    DIRECTOR_OF = "director_of", "Director of"
    TRUSTEE_OF = "trustee_of", "Trustee of"
    BENEFICIAL_OWNER_OF = "beneficial_owner_of", "Beneficial Owner of"
    MEMBER_OF = "member_of", "Member of"
    SHAREHOLDER_OF = "shareholder_of", "Shareholder of"
    HOLDS_ASSET = "holds_asset", "Holds Asset"
    OPERATES_AS = "operates_as", "Operates As"
    GUARANTOR_FOR = "guarantor_for", "Guarantor For"
    LEASES_FROM = "leases_from", "Leases From"
    PARENT_OF = "parent_of", "Parent Of"


class VaultEntity(models.Model):
    """A legal entity within a vault (person, trust, company, CC, sole prop, asset).

    Uses a single table with a JSONField for type-specific structured data.
    DATA_SCHEMAS defines the expected keys per entity_type — used by the frontend
    to render dynamic forms and by the serializer to soft-validate field keys.

    No other app may FK to this model. External references store vault_entity_id
    (plain int) and fetch via InternalGatewayService or the checkout flow.
    """

    DATA_SCHEMAS: dict = {
        "personal": {
            "id_number": {"type": "string", "label": "SA ID / Passport Number"},
            "date_of_birth": {"type": "date", "label": "Date of Birth"},
            "nationality": {"type": "string", "label": "Nationality"},
            "tax_number": {"type": "string", "label": "SARS Tax Number"},
            "address": {"type": "text", "label": "Residential Address"},
            "phone": {"type": "string", "label": "Phone"},
            "email": {"type": "email", "label": "Email"},
            "marital_status": {"type": "string", "label": "Marital Status"},
            "spouse_name": {"type": "string", "label": "Spouse Full Name"},
        },
        "trust": {
            "trust_name": {"type": "string", "label": "Trust Name"},
            "trust_number": {"type": "string", "label": "Trust Registration Number"},
            "trust_type": {"type": "string", "label": "Trust Type (inter vivos / testamentary)"},
            "master_reference": {"type": "string", "label": "Master of the High Court Reference"},
            "trustees": {"type": "list", "label": "Trustees (names)"},
            "beneficiaries": {"type": "list", "label": "Beneficiaries (names)"},
            "deed_date": {"type": "date", "label": "Trust Deed Date"},
            "tax_number": {"type": "string", "label": "Trust Tax Number"},
        },
        "company": {
            "reg_number": {"type": "string", "label": "CIPC Registration Number"},
            "vat_number": {"type": "string", "label": "VAT Number"},
            "company_type": {"type": "string", "label": "Company Type (Pty Ltd / NPC / etc.)"},
            "registration_date": {"type": "date", "label": "Registration Date"},
            "registered_address": {"type": "text", "label": "Registered Address"},
            "directors": {"type": "list", "label": "Directors"},
            "shareholders": {"type": "list", "label": "Shareholders"},
            "financial_year_end": {"type": "string", "label": "Financial Year End (MM-DD)"},
            "tax_number": {"type": "string", "label": "Income Tax Number"},
        },
        "close_corporation": {
            "reg_number": {"type": "string", "label": "CC Registration Number"},
            "vat_number": {"type": "string", "label": "VAT Number"},
            "members": {"type": "list", "label": "Members"},
            "member_interest_pct": {"type": "dict", "label": "Member Interest (%)"},
            "registered_address": {"type": "text", "label": "Registered Address"},
            "financial_year_end": {"type": "string", "label": "Financial Year End (MM-DD)"},
        },
        "sole_proprietary": {
            "owner_name": {"type": "string", "label": "Owner Full Name"},
            "trade_name": {"type": "string", "label": "Trading Name"},
            "id_number": {"type": "string", "label": "Owner SA ID Number"},
            "tax_number": {"type": "string", "label": "Tax Reference Number"},
            "vat_number": {"type": "string", "label": "VAT Number"},
            "business_address": {"type": "text", "label": "Business Address"},
            "fic_registered": {"type": "boolean", "label": "FIC Registered"},
        },
        "asset": {
            "asset_type": {"type": "string", "label": "Asset Type (property / vehicle / investment / other)"},
            "description": {"type": "text", "label": "Description"},
            "registration_number": {"type": "string", "label": "Registration / Title Deed Number"},
            "acquisition_date": {"type": "date", "label": "Acquisition Date"},
            "acquisition_value": {"type": "decimal", "label": "Acquisition Value (ZAR)"},
            "current_value": {"type": "decimal", "label": "Current Market Value (ZAR)"},
            "insured": {"type": "boolean", "label": "Insured"},
            "insurer": {"type": "string", "label": "Insurer Name"},
            "address": {"type": "text", "label": "Physical Address (if applicable)"},
        },
    }

    vault = models.ForeignKey(
        VaultOwner,
        on_delete=models.CASCADE,
        related_name="entities",
    )
    entity_type = models.CharField(max_length=30, choices=EntityType.choices)
    name = models.CharField(max_length=255, help_text="Human label, e.g. 'John Smith', 'Acme (Pty) Ltd'")
    data = models.JSONField(default=dict, help_text="Type-specific structured fields per DATA_SCHEMAS")
    chroma_id = models.CharField(max_length=128, blank=True, help_text="ChromaDB base ID in volt_entities")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vault Entity"
        verbose_name_plural = "Vault Entities"
        indexes = [
            models.Index(fields=["vault", "entity_type"]),
            models.Index(fields=["vault", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()}: {self.name}"


class EntityRelationship(models.Model):
    """A directed graph edge between two VaultEntity nodes in the same vault.

    Represents relationships such as "John Smith IS_DIRECTOR_OF Acme Ltd".
    Both nodes must belong to the same vault (enforced in serializer validate()).

    vault is denormalized from from_entity for fast vault-scoped queries:
      EntityRelationship.objects.filter(vault=owner.vault)
    without joining through from_entity.
    """

    vault = models.ForeignKey(
        VaultOwner,
        on_delete=models.CASCADE,
        related_name="relationships",
    )
    from_entity = models.ForeignKey(
        VaultEntity,
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )
    to_entity = models.ForeignKey(
        VaultEntity,
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )
    relationship_type = models.CharField(max_length=40, choices=RelationshipType.choices)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional: share_pct, effective_date, end_date, notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Entity Relationship"
        verbose_name_plural = "Entity Relationships"
        unique_together = [("from_entity", "to_entity", "relationship_type")]

    def __str__(self):
        return f"{self.from_entity.name} → {self.get_relationship_type_display()} → {self.to_entity.name}"


class FieldVerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    SELF_ATTESTED = "self_attested", "Self-attested"
    DOCUMENT_BACKED = "document_backed", "Backed by Verified Document"
    OFFICIAL_SOURCE = "official_source", "Verified against Official Source"
    REJECTED = "rejected", "Rejected"


class FieldExtractionSource(models.TextChoices):
    CLIENT_OCR = "client_ocr", "Client-side OCR"
    MANUAL_ENTRY = "manual_entry", "Manual Entry"
    API_LOOKUP = "api_lookup", "External API Lookup"
    AI_EXTRACTION = "ai_extraction", "Server AI Extraction"


class EntityDataField(models.Model):
    """Per-field record for a VaultEntity.

    While VaultEntity.data (JSONField) holds the current flat dict for fast reads,
    EntityDataField provides per-field provenance: who set it, from which
    source document version, verification status, and expiry.

    Writes to VaultEntity.data should be mirrored here for auditable fields.
    """

    entity = models.ForeignKey(
        VaultEntity,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    field_key = models.CharField(
        max_length=100,
        help_text="Matches a key in DATA_SCHEMAS / EntitySchema (e.g. 'id_number')",
    )
    value = models.JSONField(help_text="The field value (string/number/list/dict)")

    verification_status = models.CharField(
        max_length=30,
        choices=FieldVerificationStatus.choices,
        default=FieldVerificationStatus.UNVERIFIED,
    )
    verification_source = models.CharField(max_length=255, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True)

    # Provenance — which DocumentVersion this field was extracted from (if any)
    source_document_version = models.ForeignKey(
        "the_volt.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extracted_fields",
    )
    extraction_source = models.CharField(
        max_length=30,
        choices=FieldExtractionSource.choices,
        default=FieldExtractionSource.MANUAL_ENTRY,
    )

    expiry_date = models.DateField(null=True, blank=True)
    chroma_id = models.CharField(max_length=128, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["entity", "field_key"]
        verbose_name = "Entity Data Field"
        verbose_name_plural = "Entity Data Fields"
        unique_together = [("entity", "field_key")]

    def __str__(self):
        return f"{self.entity.name}.{self.field_key}"

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()

"""
The Volt — Entity Schema Registry.

Schemas define the expected fields for each entity type, per country.
They are stored in the database so they can evolve without code changes
and can support multiple countries out of the box.

Each EntitySchema is a versioned record. The active schema for a given
(entity_type, country_code) pair is the one with is_active=True and
the highest version number.

Field definition format (each item in the `fields` JSONField):
{
    "key":         "id_number",          # machine key used in VaultEntity.data
    "label":       "SA ID / Passport",   # human label shown in UI
    "type":        "string",             # string | text | date | decimal | boolean | list | dict | email
    "required":    true,                 # whether the field is mandatory
    "order":       1,                    # display order in the form
    "help_text":   "...",               # optional tooltip / help
    "options":     ["option1", ...],     # for enum/select types
    "depends_on":  "other_key",          # show only when other_key has a truthy value
}
"""
from django.db import models

from apps.the_volt.entities.models import EntityType


class FieldType(models.TextChoices):
    STRING = "string", "String"
    TEXT = "text", "Long Text"
    DATE = "date", "Date"
    DECIMAL = "decimal", "Decimal Number"
    BOOLEAN = "boolean", "Boolean"
    LIST = "list", "List"
    DICT = "dict", "Dictionary"
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone Number"
    SELECT = "select", "Select (enum)"
    FILE = "file", "File Reference"


class EntitySchema(models.Model):
    """Versioned schema definition for one entity type in one country.

    The frontend fetches the active schema to render dynamic forms.
    The serializer uses it to validate VaultEntity.data field keys.

    To update a schema: create a new version with is_active=True (the old
    version is automatically deactivated by the save() override).
    """

    entity_type = models.CharField(max_length=30, choices=EntityType.choices)
    country_code = models.CharField(
        max_length=2,
        default="ZA",
        help_text="ISO 3166-1 alpha-2 country code. 'ZA' = South Africa.",
    )
    version = models.PositiveIntegerField(default=1)
    label = models.CharField(max_length=100, help_text="Human label for this entity type, e.g. 'South African Company'")
    description = models.TextField(blank=True, help_text="Guidance shown above the form")
    fields = models.JSONField(
        default=list,
        help_text="Ordered list of field definition objects (see module docstring for format)",
    )
    is_active = models.BooleanField(default=True, help_text="Only one schema per (entity_type, country_code) can be active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-version"]
        verbose_name = "Entity Schema"
        verbose_name_plural = "Entity Schemas"
        unique_together = [("entity_type", "country_code", "version")]
        indexes = [
            models.Index(fields=["entity_type", "country_code", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()} [{self.country_code}] v{self.version}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other versions for this (entity_type, country_code)
            EntitySchema.objects.filter(
                entity_type=self.entity_type,
                country_code=self.country_code,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls, entity_type: str, country_code: str = "ZA") -> "EntitySchema | None":
        """Return the active schema for (entity_type, country_code), or None."""
        return cls.objects.filter(
            entity_type=entity_type,
            country_code=country_code,
            is_active=True,
        ).first()

    @classmethod
    def get_fields_dict(cls, entity_type: str, country_code: str = "ZA") -> list[dict]:
        """Return the fields list for the active schema, or [] if not found."""
        schema = cls.get_active(entity_type, country_code)
        return schema.fields if schema else []

    def get_field_keys(self) -> set[str]:
        """Return the set of field keys defined in this schema."""
        return {f["key"] for f in self.fields if isinstance(f, dict) and "key" in f}

    def get_required_keys(self) -> set[str]:
        """Return the set of required field keys."""
        return {f["key"] for f in self.fields if isinstance(f, dict) and f.get("required")}


# ---------------------------------------------------------------------------
# Default ZA schemas — seeded by management command or data migration
# These match the DATA_SCHEMAS dict on VaultEntity but are now DB-driven.
# ---------------------------------------------------------------------------

ZA_DEFAULT_SCHEMAS: dict[str, dict] = {
    "personal": {
        "label": "Natural Person (South Africa)",
        "description": "An individual natural person. Use this for owners, directors, trustees, members, and tenants.",
        "fields": [
            {"key": "id_number", "label": "SA ID / Passport Number", "type": "string", "required": True, "order": 1},
            {"key": "date_of_birth", "label": "Date of Birth", "type": "date", "required": False, "order": 2},
            {"key": "nationality", "label": "Nationality", "type": "string", "required": False, "order": 3},
            {"key": "tax_number", "label": "SARS Tax Number", "type": "string", "required": False, "order": 4},
            {"key": "address", "label": "Residential Address", "type": "text", "required": False, "order": 5},
            {"key": "phone", "label": "Phone", "type": "phone", "required": False, "order": 6},
            {"key": "email", "label": "Email", "type": "email", "required": False, "order": 7},
            {"key": "marital_status", "label": "Marital Status", "type": "select", "required": False, "order": 8,
             "options": ["Single", "Married in Community", "Married out of Community", "Divorced", "Widowed"]},
            {"key": "spouse_name", "label": "Spouse Full Name", "type": "string", "required": False, "order": 9,
             "depends_on": "marital_status"},
        ],
    },
    "trust": {
        "label": "Trust (South Africa)",
        "description": "An inter vivos or testamentary trust registered with the Master of the High Court.",
        "fields": [
            {"key": "trust_name", "label": "Trust Name", "type": "string", "required": True, "order": 1},
            {"key": "trust_number", "label": "Trust Registration Number", "type": "string", "required": True, "order": 2},
            {"key": "trust_type", "label": "Trust Type", "type": "select", "required": False, "order": 3,
             "options": ["Inter Vivos", "Testamentary"]},
            {"key": "master_reference", "label": "Master of the High Court Reference", "type": "string", "required": False, "order": 4},
            {"key": "trustees", "label": "Trustees", "type": "list", "required": False, "order": 5},
            {"key": "beneficiaries", "label": "Beneficiaries", "type": "list", "required": False, "order": 6},
            {"key": "deed_date", "label": "Trust Deed Date", "type": "date", "required": False, "order": 7},
            {"key": "tax_number", "label": "Trust Tax Number", "type": "string", "required": False, "order": 8},
        ],
    },
    "company": {
        "label": "Company (South Africa)",
        "description": "An entity registered with CIPC (Pty Ltd, NPC, SOC, etc.).",
        "fields": [
            {"key": "reg_number", "label": "CIPC Registration Number", "type": "string", "required": True, "order": 1},
            {"key": "vat_number", "label": "VAT Number", "type": "string", "required": False, "order": 2},
            {"key": "company_type", "label": "Company Type", "type": "select", "required": False, "order": 3,
             "options": ["Pty Ltd", "NPC", "SOC Ltd", "RF Ltd", "Personal Liability"]},
            {"key": "registration_date", "label": "Registration Date", "type": "date", "required": False, "order": 4},
            {"key": "registered_address", "label": "Registered Address", "type": "text", "required": False, "order": 5},
            {"key": "directors", "label": "Directors", "type": "list", "required": False, "order": 6},
            {"key": "shareholders", "label": "Shareholders", "type": "list", "required": False, "order": 7},
            {"key": "financial_year_end", "label": "Financial Year End (MM-DD)", "type": "string", "required": False, "order": 8},
            {"key": "tax_number", "label": "Income Tax Number", "type": "string", "required": False, "order": 9},
        ],
    },
    "close_corporation": {
        "label": "Close Corporation (South Africa)",
        "description": "A CC registered under the Close Corporations Act 69 of 1984.",
        "fields": [
            {"key": "reg_number", "label": "CC Registration Number", "type": "string", "required": True, "order": 1},
            {"key": "vat_number", "label": "VAT Number", "type": "string", "required": False, "order": 2},
            {"key": "members", "label": "Members", "type": "list", "required": False, "order": 3},
            {"key": "member_interest_pct", "label": "Member Interest (%)", "type": "dict", "required": False, "order": 4},
            {"key": "registered_address", "label": "Registered Address", "type": "text", "required": False, "order": 5},
            {"key": "financial_year_end", "label": "Financial Year End (MM-DD)", "type": "string", "required": False, "order": 6},
        ],
    },
    "sole_proprietary": {
        "label": "Sole Proprietor (South Africa)",
        "description": "An unregistered business run by a single individual.",
        "fields": [
            {"key": "owner_name", "label": "Owner Full Name", "type": "string", "required": True, "order": 1},
            {"key": "trade_name", "label": "Trading Name", "type": "string", "required": False, "order": 2},
            {"key": "id_number", "label": "Owner SA ID Number", "type": "string", "required": True, "order": 3},
            {"key": "tax_number", "label": "Tax Reference Number", "type": "string", "required": False, "order": 4},
            {"key": "vat_number", "label": "VAT Number", "type": "string", "required": False, "order": 5},
            {"key": "business_address", "label": "Business Address", "type": "text", "required": False, "order": 6},
            {"key": "fic_registered", "label": "FIC Registered", "type": "boolean", "required": False, "order": 7},
        ],
    },
    "asset": {
        "label": "Asset",
        "description": "A property, vehicle, investment account, or other asset.",
        "fields": [
            {"key": "asset_type", "label": "Asset Type", "type": "select", "required": True, "order": 1,
             "options": ["Property", "Vehicle", "Investment", "Business Interest", "Other"]},
            {"key": "description", "label": "Description", "type": "text", "required": False, "order": 2},
            {"key": "registration_number", "label": "Registration / Title Deed Number", "type": "string", "required": False, "order": 3},
            {"key": "acquisition_date", "label": "Acquisition Date", "type": "date", "required": False, "order": 4},
            {"key": "acquisition_value", "label": "Acquisition Value (ZAR)", "type": "decimal", "required": False, "order": 5},
            {"key": "current_value", "label": "Current Market Value (ZAR)", "type": "decimal", "required": False, "order": 6},
            {"key": "insured", "label": "Insured", "type": "boolean", "required": False, "order": 7},
            {"key": "insurer", "label": "Insurer Name", "type": "string", "required": False, "order": 8, "depends_on": "insured"},
            {"key": "address", "label": "Physical Address (if applicable)", "type": "text", "required": False, "order": 9},
        ],
    },
}

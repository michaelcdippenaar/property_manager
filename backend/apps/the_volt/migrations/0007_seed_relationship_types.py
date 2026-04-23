from django.db import migrations

RELATIONSHIP_TYPES = [
    {
        "code": "director_of",
        "label": "Director of",
        "inverse_label": "Has Director",
        "description": "Individual holds a directorship. Companies Act s.66.",
        "valid_from_entity_types": ["personal"],
        "valid_to_entity_types": ["company", "close_corporation"],
        "regulatory_reference": "Companies Act s.66",
        "metadata_schema": {
            "effective_date": {"type": "date", "label": "Effective Date", "required": False},
            "end_date": {"type": "date", "label": "End Date", "required": False},
        },
        "sort_order": 10,
    },
    {
        "code": "trustee_of",
        "label": "Trustee of",
        "inverse_label": "Has Trustee",
        "description": "Individual is an authorised trustee. Trust Property Control Act s.6.",
        "valid_from_entity_types": ["personal"],
        "valid_to_entity_types": ["trust"],
        "regulatory_reference": "Trust Property Control Act s.6",
        "metadata_schema": {
            "effective_date": {"type": "date", "label": "Effective Date", "required": False},
            "letter_of_authority_ref": {"type": "string", "label": "Letters of Authority Reference", "required": False},
        },
        "sort_order": 20,
    },
    {
        "code": "beneficial_owner_of",
        "label": "Beneficial Owner of",
        "inverse_label": "Beneficially Owned by",
        "description": "Natural person who ultimately owns or controls the entity. FICA s.21 beneficial ownership disclosure.",
        "valid_from_entity_types": ["personal"],
        "valid_to_entity_types": ["company", "trust", "close_corporation", "sole_proprietary"],
        "regulatory_reference": "FICA s.21; Companies Act s.56",
        "metadata_schema": {
            "ownership_pct": {"type": "decimal", "label": "Ownership %", "required": False},
            "control_mechanism": {"type": "string", "label": "Control Mechanism", "required": False},
        },
        "sort_order": 30,
    },
    {
        "code": "member_of",
        "label": "Member of",
        "inverse_label": "Has Member",
        "description": "Member of a Close Corporation.",
        "valid_from_entity_types": ["personal"],
        "valid_to_entity_types": ["close_corporation"],
        "regulatory_reference": "Close Corporations Act s.29",
        "metadata_schema": {
            "member_interest_pct": {"type": "decimal", "label": "Member Interest %", "required": True},
            "effective_date": {"type": "date", "label": "Effective Date", "required": False},
        },
        "sort_order": 40,
    },
    {
        "code": "shareholder_of",
        "label": "Shareholder of",
        "inverse_label": "Has Shareholder",
        "description": "Holds shares in a company.",
        "valid_from_entity_types": ["personal", "company", "trust", "close_corporation"],
        "valid_to_entity_types": ["company"],
        "regulatory_reference": "Companies Act s.50-56",
        "metadata_schema": {
            "share_pct": {"type": "decimal", "label": "Share %", "required": False},
            "share_class": {"type": "string", "label": "Share Class", "required": False},
            "shares_held": {"type": "integer", "label": "Shares Held", "required": False},
        },
        "sort_order": 50,
    },
    {
        "code": "holds_asset",
        "label": "Holds Asset",
        "inverse_label": "Held by",
        "description": "Entity owns or holds a physical or financial asset.",
        "valid_from_entity_types": ["personal", "company", "trust", "close_corporation", "sole_proprietary"],
        "valid_to_entity_types": ["asset"],
        "regulatory_reference": "",
        "metadata_schema": {
            "acquisition_date": {"type": "date", "label": "Acquisition Date", "required": False},
            "ownership_pct": {"type": "decimal", "label": "Ownership %", "required": False},
        },
        "sort_order": 60,
    },
    {
        "code": "operates_as",
        "label": "Operates As",
        "inverse_label": "Operated by",
        "description": "Individual operates under a sole proprietary or trading entity.",
        "valid_from_entity_types": ["personal"],
        "valid_to_entity_types": ["sole_proprietary"],
        "regulatory_reference": "",
        "metadata_schema": {
            "effective_date": {"type": "date", "label": "Effective Date", "required": False},
        },
        "sort_order": 70,
    },
    {
        "code": "guarantor_for",
        "label": "Guarantor for",
        "inverse_label": "Guaranteed by",
        "description": "Entity stands as guarantor for another entity's obligations.",
        "valid_from_entity_types": ["personal", "company", "trust"],
        "valid_to_entity_types": ["personal", "company", "trust", "close_corporation", "sole_proprietary"],
        "regulatory_reference": "National Credit Act",
        "metadata_schema": {
            "guarantee_amount": {"type": "decimal", "label": "Guarantee Amount (ZAR)", "required": False},
            "effective_date": {"type": "date", "label": "Effective Date", "required": False},
        },
        "sort_order": 80,
    },
    {
        "code": "leases_from",
        "label": "Leases From",
        "inverse_label": "Leased to",
        "description": "Tenant entity leases a property asset from the owner.",
        "valid_from_entity_types": ["personal", "company", "trust", "close_corporation", "sole_proprietary"],
        "valid_to_entity_types": ["asset"],
        "regulatory_reference": "Rental Housing Act",
        "metadata_schema": {
            "lease_start": {"type": "date", "label": "Lease Start", "required": False},
            "lease_end": {"type": "date", "label": "Lease End", "required": False},
            "monthly_rental": {"type": "decimal", "label": "Monthly Rental (ZAR)", "required": False},
        },
        "sort_order": 90,
    },
    {
        "code": "parent_of",
        "label": "Parent of",
        "inverse_label": "Subsidiary of",
        "description": "Holding company or controlling entity of another company or CC.",
        "valid_from_entity_types": ["company", "trust"],
        "valid_to_entity_types": ["company", "close_corporation"],
        "regulatory_reference": "Companies Act s.3",
        "metadata_schema": {
            "ownership_pct": {"type": "decimal", "label": "Ownership %", "required": False},
        },
        "sort_order": 100,
    },
]


def seed_relationship_types(apps, schema_editor):
    RelationshipTypeCatalogue = apps.get_model("the_volt", "RelationshipTypeCatalogue")
    for rt in RELATIONSHIP_TYPES:
        code = rt["code"]
        defaults = {k: v for k, v in rt.items() if k != "code"}
        defaults["is_system"] = True
        defaults["is_active"] = True
        RelationshipTypeCatalogue.objects.update_or_create(code=code, defaults=defaults)


def reverse_seed_relationship_types(apps, schema_editor):
    RelationshipTypeCatalogue = apps.get_model("the_volt", "RelationshipTypeCatalogue")
    codes = [rt["code"] for rt in RELATIONSHIP_TYPES]
    RelationshipTypeCatalogue.objects.filter(code__in=codes, is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("the_volt", "0006_relationship_type_catalogue"),
    ]

    operations = [
        migrations.RunPython(
            seed_relationship_types,
            reverse_seed_relationship_types,
        ),
    ]

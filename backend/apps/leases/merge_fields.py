"""
Canonical merge field registry for Klikk lease templates.

This is the single source of truth for all merge field names that are
guaranteed to be populated at e-signing time (see esigning/services.py →
get_merge_field_context).  The AI template chat agent, field widget, and
any future validation code should import from here.
"""
from __future__ import annotations

# (category_key, field_name, short_description)
CANONICAL_MERGE_FIELDS: list[tuple[str, str, str]] = [
    # ── Landlord ──────────────────────────────────────────────────────────
    ("landlord",      "landlord_name",              "Full name (individual) or trading name (company)"),
    ("landlord",      "landlord_entity_name",        "Registered company / CC / trust name"),
    ("landlord",      "landlord_registration_no",    "Company / CC / trust registration number"),
    ("landlord",      "landlord_vat_no",             "VAT registration number"),
    ("landlord",      "landlord_representative",     "Authorised representative name (companies)"),
    ("landlord",      "landlord_representative_id",  "ID number of authorised representative"),
    ("landlord",      "landlord_title",              "Title (Mr / Ms / Dr / Pty Ltd / etc.)"),
    ("landlord",      "landlord_id",                 "SA ID number (individual landlord)"),
    ("landlord",      "landlord_contact",            "Primary contact / phone"),
    ("landlord",      "landlord_phone",              "Phone number (alias for landlord_contact)"),
    ("landlord",      "landlord_email",              "Email address"),
    ("landlord",      "landlord_physical_address",   "Physical / postal address"),
    # ── Landlord bank ─────────────────────────────────────────────────────
    ("landlord_bank", "landlord_bank_name",          "Bank name (e.g. FNB, Standard Bank)"),
    ("landlord_bank", "landlord_bank_branch_code",   "Branch / universal branch code"),
    ("landlord_bank", "landlord_bank_account_no",    "Bank account number"),
    ("landlord_bank", "landlord_bank_account_holder","Account holder name"),
    ("landlord_bank", "landlord_bank_account_type",  "Account type (cheque / savings / current)"),
    # ── Property ──────────────────────────────────────────────────────────
    ("property",      "property_address",            "Full street address of the property"),
    ("property",      "property_name",               "Estate / building / complex name"),
    ("property",      "property_description",        "Full legal or erf description"),
    ("property",      "unit_number",                 "Unit / flat / door number"),
    ("property",      "city",                        "City or town"),
    ("property",      "province",                    "Province (e.g. Western Cape)"),
    # ── Primary tenant ────────────────────────────────────────────────────
    ("tenant",        "tenant_name",                 "Full name of primary tenant"),
    ("tenant",        "tenant_id",                   "SA ID number of primary tenant"),
    ("tenant",        "tenant_phone",                "Phone number"),
    ("tenant",        "tenant_contact",              "Contact number (alias for tenant_phone)"),
    ("tenant",        "tenant_email",                "Email address"),
    ("tenant",        "tenant_address",              "Current residential address"),
    ("tenant",        "tenant_employer",             "Employer name"),
    ("tenant",        "tenant_occupation",           "Occupation / job title"),
    ("tenant",        "tenant_dob",                  "Date of birth"),
    ("tenant",        "tenant_emergency_contact",    "Emergency contact person name"),
    ("tenant",        "tenant_emergency_phone",      "Emergency contact phone number"),
    # ── Tenant 1 (numbered alias — same person as primary tenant) ─────────
    ("tenant_1",      "tenant_1_name",               "Tenant 1 full name (alias for tenant_name)"),
    ("tenant_1",      "tenant_1_id",                 "Tenant 1 SA ID number"),
    ("tenant_1",      "tenant_1_phone",              "Tenant 1 phone"),
    ("tenant_1",      "tenant_1_email",              "Tenant 1 email"),
    ("tenant_1",      "tenant_1_address",            "Tenant 1 address"),
    ("tenant_1",      "tenant_1_employer",           "Tenant 1 employer"),
    ("tenant_1",      "tenant_1_occupation",         "Tenant 1 occupation"),
    ("tenant_1",      "tenant_1_dob",                "Tenant 1 date of birth"),
    ("tenant_1",      "tenant_1_emergency_contact",  "Tenant 1 emergency contact"),
    ("tenant_1",      "tenant_1_emergency_phone",    "Tenant 1 emergency phone"),
    ("tenant_1",      "primary_tenant_payment_reference", "Primary tenant payment reference (EFT)"),
    ("tenant_1",      "cotenant_1_payment_reference", "Co-tenant 1 payment reference (EFT)"),
    # ── Tenant 2 ──────────────────────────────────────────────────────────
    ("tenant_2",      "tenant_2_name",               "Tenant 2 full name"),
    ("tenant_2",      "tenant_2_id",                 "Tenant 2 SA ID number"),
    ("tenant_2",      "tenant_2_phone",              "Tenant 2 phone"),
    ("tenant_2",      "tenant_2_email",              "Tenant 2 email"),
    ("tenant_2",      "tenant_2_address",            "Tenant 2 address"),
    ("tenant_2",      "tenant_2_employer",           "Tenant 2 employer"),
    ("tenant_2",      "tenant_2_occupation",         "Tenant 2 occupation"),
    ("tenant_2",      "tenant_2_dob",                "Tenant 2 date of birth"),
    ("tenant_2",      "tenant_2_emergency_contact",  "Tenant 2 emergency contact"),
    ("tenant_2",      "tenant_2_emergency_phone",    "Tenant 2 emergency phone"),
    ("tenant_2",      "cotenant_2_payment_reference", "Co-tenant 2 payment reference (EFT)"),
    # ── Tenant 3 ──────────────────────────────────────────────────────────
    ("tenant_3",      "tenant_3_name",               "Tenant 3 full name"),
    ("tenant_3",      "tenant_3_id",                 "Tenant 3 SA ID number"),
    ("tenant_3",      "tenant_3_phone",              "Tenant 3 phone"),
    ("tenant_3",      "tenant_3_email",              "Tenant 3 email"),
    ("tenant_3",      "tenant_3_address",            "Tenant 3 address"),
    ("tenant_3",      "tenant_3_employer",           "Tenant 3 employer"),
    ("tenant_3",      "tenant_3_occupation",         "Tenant 3 occupation"),
    ("tenant_3",      "tenant_3_dob",                "Tenant 3 date of birth"),
    ("tenant_3",      "tenant_3_emergency_contact",  "Tenant 3 emergency contact"),
    ("tenant_3",      "tenant_3_emergency_phone",    "Tenant 3 emergency phone"),
    ("tenant_3",      "cotenant_3_payment_reference", "Co-tenant 3 payment reference (EFT)"),
    # ── Co-tenants summary ────────────────────────────────────────────────
    ("co_tenants",    "co_tenants",                  "Comma-separated list of all co-tenant names"),
    # ── Occupants 1–4 ─────────────────────────────────────────────────────
    ("occupant_1",    "occupant_1_name",             "Occupant 1 full name"),
    ("occupant_1",    "occupant_1_id",               "Occupant 1 SA ID number"),
    ("occupant_1",    "occupant_1_relationship",     "Occupant 1 relationship to tenant"),
    ("occupant_2",    "occupant_2_name",             "Occupant 2 full name"),
    ("occupant_2",    "occupant_2_id",               "Occupant 2 SA ID number"),
    ("occupant_2",    "occupant_2_relationship",     "Occupant 2 relationship to tenant"),
    ("occupant_3",    "occupant_3_name",             "Occupant 3 full name"),
    ("occupant_3",    "occupant_3_id",               "Occupant 3 SA ID number"),
    ("occupant_3",    "occupant_3_relationship",     "Occupant 3 relationship to tenant"),
    ("occupant_4",    "occupant_4_name",             "Occupant 4 full name"),
    ("occupant_4",    "occupant_4_id",               "Occupant 4 SA ID number"),
    ("occupant_4",    "occupant_4_relationship",     "Occupant 4 relationship to tenant"),
    # ── Lease terms ───────────────────────────────────────────────────────
    ("lease_terms",   "lease_start",                 "Lease commencement date"),
    ("lease_terms",   "lease_end",                   "Lease expiry / end date"),
    ("lease_terms",   "monthly_rent",                "Monthly rental amount (numeric)"),
    ("lease_terms",   "monthly_rent_words",          "Monthly rental amount in words"),
    ("lease_terms",   "deposit",                     "Deposit amount (numeric)"),
    ("lease_terms",   "deposit_words",               "Deposit amount in words"),
    ("lease_terms",   "notice_period_days",          "Notice period in days (minimum 20 business days per RHA)"),
    ("lease_terms",   "water_included",              "Whether water is included (Yes/No)"),
    ("lease_terms",   "electricity_prepaid",         "Whether electricity is prepaid (Yes/No)"),
    # ── Property services & facilities (Feature 3) ─────────────────────────
    ("services",      "water_arrangement",           "Water arrangement key: included | not_included"),
    ("services",      "water_arrangement_label",     "Water arrangement (human-readable)"),
    ("services",      "electricity_arrangement",     "Electricity arrangement key: prepaid | eskom_direct | included | not_included"),
    ("services",      "electricity_arrangement_label", "Electricity arrangement (human-readable)"),
    ("services",      "gardening_service_included",  "Gardening service included (boolean)"),
    ("services",      "gardening_service_included_label", "Gardening service included (Yes/No)"),
    ("services",      "wifi_included",               "Wifi included (boolean)"),
    ("services",      "wifi_included_label",         "Wifi included (Yes/No)"),
    ("services",      "security_service_included",   "Armed response / security service included (boolean)"),
    ("services",      "security_service_included_label", "Armed response / security service included (Yes/No)"),
    ("lease_terms",   "max_occupants",               "Maximum number of authorised occupants"),
    ("lease_terms",   "payment_reference",           "Payment reference for EFT (legacy alias for primary_tenant_payment_reference)"),
    ("lease_terms",   "lease_number",                "Unique lease reference number"),
]

# Fast O(1) lookup set — use this for field name validation
CANONICAL_FIELD_NAMES: frozenset[str] = frozenset(f for _, f, _ in CANONICAL_MERGE_FIELDS)

# Human-readable category labels
_CATEGORY_LABELS: dict[str, str] = {
    "landlord":      "Landlord",
    "landlord_bank": "Landlord Bank",
    "property":      "Property",
    "tenant":        "Tenant (primary)",
    "tenant_1":      "Tenant 1 (numbered alias for primary)",
    "tenant_2":      "Tenant 2",
    "tenant_3":      "Tenant 3",
    "co_tenants":    "Co-Tenants",
    "occupant_1":    "Occupant 1",
    "occupant_2":    "Occupant 2",
    "occupant_3":    "Occupant 3",
    "occupant_4":    "Occupant 4",
    "lease_terms":   "Lease Terms",
    "services":      "Property Services",
}


def build_merge_fields_prompt_block() -> str:
    """
    Return the 'Available Merge Fields' section for the AI system prompt.
    Groups fields by category in a compact multi-line format (~550 tokens).
    """
    # Group field names by category (preserving insertion order)
    from collections import OrderedDict
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for cat, field, _ in CANONICAL_MERGE_FIELDS:
        groups.setdefault(cat, []).append(field)

    lines = [
        "## Available Merge Fields",
        "Use {{ field_name }} syntax. All fields below are populated at signing time.",
        "For COMPANY landlords use: landlord_entity_name, landlord_registration_no, landlord_vat_no, landlord_representative.",
        "For INDIVIDUAL landlords use: landlord_name, landlord_id.",
        "",
    ]
    for cat, fields in groups.items():
        label = _CATEGORY_LABELS.get(cat, cat)
        lines.append(f"{label}: {', '.join(fields)}")

    return "\n".join(lines)

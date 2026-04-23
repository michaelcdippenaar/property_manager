from django.db import migrations

DOCUMENTS = [
    # ── Asset - Property (sort_order 600-619) ────────────────────────────────

    {
        "code": "title_deed",
        "label": "Title Deed",
        "issuing_authority": "Deeds Office",
        "is_primary_identity_doc": True,
        "regulatory_reference": "Deeds Registries Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 600,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["Title Deed", "Deed of Transfer"],
        "is_active": True,
        "classification_signals": (
            "Deeds Office title deed or deed of transfer. "
            "Property description (Erf/Portion/Unit), title deed number, registered owner name, "
            "extent in square metres. Deeds Office stamp and registrar signature."
        ),
        "extraction_schema": {
            "property_description": {"type": "text",    "label": "Property Description",  "required": True},
            "erf_number":           {"type": "string",  "label": "ERF / Portion Number",  "required": False},
            "title_deed_number":    {"type": "string",  "label": "Title Deed Number",     "required": True},
            "registered_owner":     {"type": "string",  "label": "Registered Owner",      "required": True},
            "extent_m2":            {"type": "decimal", "label": "Extent (m²)",           "required": False},
            "purchase_price":       {"type": "decimal", "label": "Purchase Price (ZAR)",  "required": False},
            "registration_date":    {"type": "date",    "label": "Registration Date",     "required": False},
        },
    },
    {
        "code": "rates_clearance",
        "label": "Rates Clearance Certificate",
        "issuing_authority": "Municipality",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Municipal Systems Act",
        "default_validity_days": 90,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 601,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Municipal rates clearance certificate. "
            "Property address, account number, clearance amount paid, valid period. Municipality stamp."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address",  "required": True},
            "account_number":   {"type": "string",  "label": "Account Number",    "required": False},
            "amount_paid":      {"type": "decimal", "label": "Amount Paid (ZAR)", "required": False},
            "valid_from":       {"type": "date",    "label": "Valid From",        "required": True},
            "valid_to":         {"type": "date",    "label": "Valid To",          "required": True},
            "municipality":     {"type": "string",  "label": "Municipality",      "required": False},
        },
    },
    {
        "code": "building_plans",
        "label": "Approved Building Plans",
        "issuing_authority": "Municipality",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Building Regulations and Building Standards Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 602,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Municipality-approved building plans. "
            "Stamp showing approval date, plan number, property address. "
            "Architectural drawings. May reference SANS 10400."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",   "label": "Property Address",                         "required": True},
            "plan_number":      {"type": "string", "label": "Plan Number",                              "required": False},
            "approval_date":    {"type": "date",   "label": "Approval Date",                            "required": False},
            "plan_type":        {"type": "string", "label": "Plan Type (new build / alterations / additions)", "required": False},
        },
    },
    {
        "code": "occupancy_certificate",
        "label": "Certificate of Occupancy",
        "issuing_authority": "Municipality",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Building Regulations and Building Standards Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 603,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["COO", "Occupation Certificate"],
        "is_active": True,
        "classification_signals": (
            "Municipality certificate of occupancy. "
            "Confirms building complies with approved plans. "
            "Property address, certificate number, date issued, building inspector signature."
        ),
        "extraction_schema": {
            "property_address":  {"type": "text",   "label": "Property Address",    "required": True},
            "certificate_number": {"type": "string", "label": "Certificate Number", "required": False},
            "date_issued":       {"type": "date",   "label": "Date Issued",         "required": True},
            "building_type":     {"type": "string", "label": "Building Type",       "required": False},
        },
    },
    {
        "code": "electrical_coc",
        "label": "Electrical Compliance Certificate (COC)",
        "issuing_authority": "Licensed Electrician",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Electrical Installation Regulations (OHS Act)",
        "default_validity_days": 730,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 604,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["Electrical COC", "Certificate of Compliance"],
        "is_active": True,
        "classification_signals": (
            "Electrical certificate of compliance. "
            "Electrician name and registration number, property address, certificate number, "
            "date issued, expiry date. DoL format."
        ),
        "extraction_schema": {
            "property_address":         {"type": "text",   "label": "Property Address",           "required": True},
            "certificate_number":       {"type": "string", "label": "Certificate Number",         "required": True},
            "electrician_name":         {"type": "string", "label": "Electrician Name",           "required": True},
            "electrician_registration": {"type": "string", "label": "Electrician Registration No.", "required": False},
            "date_issued":              {"type": "date",   "label": "Date Issued",                "required": True},
            "expiry_date":              {"type": "date",   "label": "Expiry Date",                "required": False},
        },
    },
    {
        "code": "gas_coc",
        "label": "Gas Compliance Certificate",
        "issuing_authority": "Registered Gas Practitioner",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Pressure Equipment Regulations (OHS Act)",
        "default_validity_days": 730,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 605,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Gas compliance certificate. "
            "LPGAS practitioner name and registration, property address, certificate number. "
            "Covers gas appliances and piping."
        ),
        "extraction_schema": {
            "property_address":  {"type": "text",   "label": "Property Address",  "required": True},
            "certificate_number": {"type": "string", "label": "Certificate Number", "required": False},
            "practitioner_name": {"type": "string", "label": "Practitioner Name", "required": True},
            "date_issued":       {"type": "date",   "label": "Date Issued",       "required": True},
        },
    },
    {
        "code": "plumbing_coc",
        "label": "Plumbing Compliance Certificate",
        "issuing_authority": "Registered Plumber",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Building Regulations",
        "default_validity_days": 730,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 606,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Plumbing compliance certificate. "
            "Registered plumber name and PIRB number, property address. "
            "Covers water supply and drainage."
        ),
        "extraction_schema": {
            "property_address":  {"type": "text",   "label": "Property Address",  "required": True},
            "certificate_number": {"type": "string", "label": "Certificate Number", "required": False},
            "plumber_name":      {"type": "string", "label": "Plumber Name",      "required": True},
            "date_issued":       {"type": "date",   "label": "Date Issued",       "required": True},
        },
    },
    {
        "code": "electric_fence_coc",
        "label": "Electric Fence System Certificate",
        "issuing_authority": "Registered Installer",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Electric Fence System Regulations (OHS Act)",
        "default_validity_days": 730,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 607,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Electric fence certificate of compliance. "
            "Installer name and ECASA registration number, property address, certificate number."
        ),
        "extraction_schema": {
            "property_address":  {"type": "text",   "label": "Property Address",  "required": True},
            "certificate_number": {"type": "string", "label": "Certificate Number", "required": False},
            "installer_name":    {"type": "string", "label": "Installer Name",    "required": True},
            "date_issued":       {"type": "date",   "label": "Date Issued",       "required": True},
        },
    },
    {
        "code": "beetle_certificate",
        "label": "Beetle / Pest Clearance Certificate",
        "issuing_authority": "Registered Pest Control Operator",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Pest Control Operators Act",
        "default_validity_days": 180,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 608,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Beetle or pest clearance certificate. "
            "Inspector name and registration number, property address, inspection date, "
            "result (clear / treated). Wood-destroying insect inspection."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",   "label": "Property Address",               "required": True},
            "date_inspected":   {"type": "date",   "label": "Date Inspected",                 "required": True},
            "inspector_name":   {"type": "string", "label": "Inspector Name",                 "required": True},
            "result":           {"type": "string", "label": "Result (clear / treatment required)", "required": True},
        },
    },
    {
        "code": "zoning_certificate",
        "label": "Zoning Certificate",
        "issuing_authority": "Municipality",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Spatial Planning and Land Use Management Act (SPLUMA)",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 609,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Municipal zoning certificate. "
            "Property address or ERF number, zoning type (residential / commercial / mixed use), "
            "permitted uses, date issued."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",   "label": "Property Address", "required": True},
            "zoning_type":      {"type": "string", "label": "Zoning Type",      "required": True},
            "permitted_use":    {"type": "text",   "label": "Permitted Use",    "required": False},
            "date_issued":      {"type": "date",   "label": "Date Issued",      "required": False},
        },
    },
    {
        "code": "valuation_report",
        "label": "Property Valuation Report",
        "issuing_authority": "Registered Valuator",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Property Valuers Profession Act",
        "default_validity_days": 180,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 610,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Property valuation report on valuator letterhead. "
            "SACPVP registration number. Property address, market value, valuation date, "
            "methodology (sales comparison / income / cost)."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address", "required": True},
            "market_value":     {"type": "decimal", "label": "Market Value (ZAR)", "required": True},
            "valuator_name":    {"type": "string",  "label": "Valuator Name",    "required": True},
            "valuation_date":   {"type": "date",    "label": "Valuation Date",   "required": True},
            "methodology":      {"type": "string",  "label": "Methodology",      "required": False},
        },
    },
    {
        "code": "hoa_rules",
        "label": "HOA / Body Corporate Rules",
        "issuing_authority": "HOA / Body Corporate",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Sectional Titles Schemes Management Act; HOA constitution",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 611,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["Conduct Rules", "HOA Rules", "Body Corporate Rules"],
        "is_active": True,
        "classification_signals": (
            "HOA or body corporate rules and conduct rules. "
            "Scheme name, managing agent, levy schedule, conduct rules."
        ),
        "extraction_schema": {
            "scheme_name":    {"type": "string",  "label": "Scheme / HOA Name",           "required": True},
            "managing_agent": {"type": "string",  "label": "Managing Agent",              "required": False},
            "levy_amount":    {"type": "decimal", "label": "Monthly Levy (ZAR)",          "required": False},
            "special_rules":  {"type": "text",    "label": "Special Rules / Restrictions", "required": False},
        },
    },
    {
        "code": "levy_clearance",
        "label": "Levy Clearance Certificate",
        "issuing_authority": "Body Corporate / HOA",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Sectional Titles Schemes Management Act",
        "default_validity_days": 90,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 612,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Body corporate or HOA levy clearance certificate. "
            "Scheme name, unit number, amount paid, valid period. Confirms no outstanding levies."
        ),
        "extraction_schema": {
            "scheme_name":  {"type": "string",  "label": "Scheme Name",        "required": True},
            "unit_number":  {"type": "string",  "label": "Unit Number",        "required": False},
            "amount_paid":  {"type": "decimal", "label": "Amount Paid (ZAR)",  "required": False},
            "valid_to":     {"type": "date",    "label": "Valid To",           "required": True},
        },
    },
    {
        "code": "survey_diagram",
        "label": "Survey / SG Diagram",
        "issuing_authority": "Surveyor General",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Land Survey Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 613,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["SG Diagram", "General Plan"],
        "is_active": True,
        "classification_signals": (
            "Surveyor General diagram or general plan. "
            "SG number, property description, extent, surveyor name, approval date. "
            "Technical survey drawing."
        ),
        "extraction_schema": {
            "property_description": {"type": "text",    "label": "Property Description", "required": True},
            "sg_number":            {"type": "string",  "label": "SG Diagram Number",    "required": False},
            "extent_m2":            {"type": "decimal", "label": "Extent (m²)",          "required": False},
            "surveyor":             {"type": "string",  "label": "Surveyor Name",        "required": False},
        },
    },
    {
        "code": "water_certificate",
        "label": "Water Use Licence / Certificate",
        "issuing_authority": "Department of Water and Sanitation",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Water Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 614,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "DWS water use licence. "
            "Property address, water use type (irrigation / industrial / domestic), "
            "licence number, date issued."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",   "label": "Property Address",  "required": True},
            "water_use_type":   {"type": "string", "label": "Water Use Type",    "required": False},
            "licence_number":   {"type": "string", "label": "Licence Number",    "required": False},
            "date_issued":      {"type": "date",   "label": "Date Issued",       "required": False},
        },
    },
    {
        "code": "otp",
        "label": "Offer to Purchase (OTP)",
        "issuing_authority": "Buyer / Estate Agent",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Alienation of Land Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 615,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["OTP", "Offer to Purchase", "Agreement of Sale"],
        "is_active": True,
        "classification_signals": (
            "Offer to purchase or agreement of sale. "
            "Buyer and seller names, property address, purchase price, date signed, "
            "conditions (suspensive conditions, bond clause)."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address",       "required": True},
            "buyer_name":       {"type": "string",  "label": "Buyer Name",             "required": True},
            "seller_name":      {"type": "string",  "label": "Seller Name",            "required": True},
            "purchase_price":   {"type": "decimal", "label": "Purchase Price (ZAR)",   "required": True},
            "date_signed":      {"type": "date",    "label": "Date Signed",            "required": True},
            "conditions":       {"type": "text",    "label": "Suspensive Conditions",  "required": False},
        },
    },
    {
        "code": "bond_statement",
        "label": "Bond / Mortgage Statement",
        "issuing_authority": "Bank",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Credit Act",
        "default_validity_days": 30,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 616,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Bank home loan / bond statement. "
            "Property address, account number, outstanding balance, monthly instalment, "
            "interest rate, bank name."
        ),
        "extraction_schema": {
            "property_address":    {"type": "text",    "label": "Property Address",           "required": True},
            "account_number":      {"type": "string",  "label": "Bond Account Number",        "required": True},
            "outstanding_balance": {"type": "decimal", "label": "Outstanding Balance (ZAR)",  "required": True},
            "monthly_instalment":  {"type": "decimal", "label": "Monthly Instalment (ZAR)",   "required": False},
            "interest_rate":       {"type": "decimal", "label": "Interest Rate (%)",          "required": False},
            "bank_name":           {"type": "string",  "label": "Bank Name",                 "required": True},
        },
    },
    {
        "code": "rental_agreement",
        "label": "Rental / Lease Agreement",
        "issuing_authority": "Landlord / Agent",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Rental Housing Act; Consumer Protection Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 617,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["Lease Agreement", "Rental Contract"],
        "is_active": True,
        "classification_signals": (
            "Residential or commercial lease agreement. "
            "Landlord and tenant names, property address, rental amount, lease period, deposit amount. "
            "May be signed electronically."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address",       "required": True},
            "landlord_name":    {"type": "string",  "label": "Landlord Name",          "required": True},
            "tenant_name":      {"type": "string",  "label": "Tenant Name",            "required": True},
            "rental_amount":    {"type": "decimal", "label": "Monthly Rental (ZAR)",   "required": True},
            "lease_start":      {"type": "date",    "label": "Lease Start Date",       "required": True},
            "lease_end":        {"type": "date",    "label": "Lease End Date",         "required": False},
            "deposit":          {"type": "decimal", "label": "Deposit (ZAR)",          "required": False},
        },
    },
    {
        "code": "property_insurance",
        "label": "Property Insurance Policy",
        "issuing_authority": "Insurer",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Short-term Insurance Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 618,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Property insurance policy schedule. "
            "Insurer name, policy number, property address, cover amount (buildings / contents), "
            "premium, expiry date."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address",  "required": True},
            "insurer_name":     {"type": "string",  "label": "Insurer Name",      "required": True},
            "policy_number":    {"type": "string",  "label": "Policy Number",     "required": True},
            "cover_amount":     {"type": "decimal", "label": "Cover Amount (ZAR)", "required": False},
            "premium":          {"type": "decimal", "label": "Premium (ZAR)",     "required": False},
            "expiry_date":      {"type": "date",    "label": "Expiry Date",       "required": True},
        },
    },
    {
        "code": "municipal_valuation",
        "label": "Municipal Valuation Roll Entry",
        "issuing_authority": "Municipality",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Municipal Property Rates Act",
        "default_validity_days": None,
        "ownership_scope": "asset_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 619,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Municipal valuation roll entry or supplementary valuation notice. "
            "Property address, ERF number, municipal value, property category, valuation date."
        ),
        "extraction_schema": {
            "property_address": {"type": "text",    "label": "Property Address",     "required": True},
            "municipal_value":  {"type": "decimal", "label": "Municipal Value (ZAR)", "required": True},
            "valuation_date":   {"type": "date",    "label": "Valuation Date",       "required": True},
            "category":         {"type": "string",  "label": "Property Category",    "required": False},
        },
    },

    # ── Asset - Vehicle (sort_order 700-705) ─────────────────────────────────

    {
        "code": "vehicle_registration",
        "label": "Vehicle Registration Certificate (NaTIS)",
        "issuing_authority": "DLTC / eNaTIS",
        "is_primary_identity_doc": True,
        "regulatory_reference": "National Road Traffic Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 700,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["NaTIS", "Vehicle Registration"],
        "is_active": True,
        "classification_signals": (
            "NaTIS vehicle registration certificate. "
            "Registration number, VIN, engine number, make, model, year, registered owner name."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string",  "label": "Registration Number", "required": True},
            "vin":                 {"type": "string",  "label": "VIN Number",          "required": True},
            "make":                {"type": "string",  "label": "Make",                "required": True},
            "model":               {"type": "string",  "label": "Model",               "required": True},
            "year":                {"type": "integer", "label": "Year",                "required": True},
            "owner_name":          {"type": "string",  "label": "Registered Owner",    "required": True},
            "registration_date":   {"type": "date",    "label": "Registration Date",   "required": False},
        },
    },
    {
        "code": "vehicle_licence_disc",
        "label": "Vehicle Licence Disc",
        "issuing_authority": "DLTC",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Road Traffic Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 701,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Annual vehicle licence disc. "
            "Registration number, expiry month/year, licence number. "
            "Small circular disc displayed on windscreen."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string", "label": "Registration Number", "required": True},
            "expiry_date":         {"type": "date",   "label": "Expiry Date",         "required": True},
            "licence_number":      {"type": "string", "label": "Licence Number",      "required": False},
        },
    },
    {
        "code": "vehicle_roadworthy",
        "label": "Roadworthy Certificate (ACR)",
        "issuing_authority": "Testing Station",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Road Traffic Act",
        "default_validity_days": 60,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 702,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": ["ACR", "Roadworthy Certificate"],
        "is_active": True,
        "classification_signals": (
            "Authorised roadworthy test certificate. "
            "Registration number, make and model, testing station name and authorisation number, "
            "date issued, valid for 60 days."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string", "label": "Registration Number", "required": True},
            "testing_station":     {"type": "string", "label": "Testing Station",     "required": True},
            "date_issued":         {"type": "date",   "label": "Date Issued",         "required": True},
            "expiry_date":         {"type": "date",   "label": "Expiry Date",         "required": False},
        },
    },
    {
        "code": "vehicle_insurance",
        "label": "Vehicle Insurance Policy",
        "issuing_authority": "Insurer",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Short-term Insurance Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 703,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Vehicle insurance policy schedule. "
            "Registration number, insurer name, policy number, cover type (comprehensive / third party), "
            "premium, expiry date."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string",  "label": "Registration Number", "required": True},
            "insurer_name":        {"type": "string",  "label": "Insurer Name",        "required": True},
            "policy_number":       {"type": "string",  "label": "Policy Number",       "required": True},
            "cover_type":          {"type": "string",  "label": "Cover Type",          "required": False},
            "premium":             {"type": "decimal", "label": "Premium (ZAR)",       "required": False},
            "expiry_date":         {"type": "date",    "label": "Expiry Date",         "required": True},
        },
    },
    {
        "code": "vehicle_finance_agreement",
        "label": "Vehicle Finance Agreement",
        "issuing_authority": "Bank / Finance House",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Credit Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 704,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Vehicle finance or instalment sale agreement. "
            "Registration number, financier name, account number, outstanding balance, "
            "monthly instalment, balloon payment if applicable."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string",  "label": "Registration Number",      "required": True},
            "financier":           {"type": "string",  "label": "Financier Name",           "required": True},
            "account_number":      {"type": "string",  "label": "Account Number",           "required": False},
            "outstanding_balance": {"type": "decimal", "label": "Outstanding Balance (ZAR)", "required": False},
            "monthly_instalment":  {"type": "decimal", "label": "Monthly Instalment (ZAR)", "required": False},
        },
    },
    {
        "code": "vehicle_settlement_letter",
        "label": "Vehicle Settlement / NaTIS Letter",
        "issuing_authority": "Bank",
        "is_primary_identity_doc": False,
        "regulatory_reference": "National Credit Act",
        "default_validity_days": 30,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 705,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Settlement letter from bank confirming outstanding settlement amount for vehicle. "
            "Registration number, VIN, settlement amount valid for 30 days."
        ),
        "extraction_schema": {
            "registration_number": {"type": "string",  "label": "Registration Number",   "required": True},
            "financier":           {"type": "string",  "label": "Financier Name",         "required": True},
            "settlement_amount":   {"type": "decimal", "label": "Settlement Amount (ZAR)", "required": True},
            "date_issued":         {"type": "date",    "label": "Date Issued",            "required": True},
        },
    },

    # ── Asset - Financial (sort_order 800-804) ───────────────────────────────

    {
        "code": "investment_statement",
        "label": "Investment / Portfolio Statement",
        "issuing_authority": "Fund Manager / FSP",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Financial Advisory and Intermediary Services Act",
        "default_validity_days": 90,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 800,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Investment or portfolio statement. "
            "Investor name, fund name, portfolio value, asset allocation breakdown, date. FSP letterhead."
        ),
        "extraction_schema": {
            "investor_name": {"type": "string",  "label": "Investor Name",          "required": True},
            "fund_name":     {"type": "string",  "label": "Fund / Portfolio Name",  "required": True},
            "value":         {"type": "decimal", "label": "Portfolio Value (ZAR)",  "required": True},
            "date":          {"type": "date",    "label": "Statement Date",         "required": True},
            "fund_manager":  {"type": "string",  "label": "Fund Manager",           "required": False},
        },
    },
    {
        "code": "retirement_fund_statement",
        "label": "Retirement Fund / Pension Statement",
        "issuing_authority": "Retirement Fund",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Pension Funds Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 801,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Retirement annuity, pension or provident fund statement. "
            "Member name, fund name, fund credit / value, contributions, projected retirement date."
        ),
        "extraction_schema": {
            "member_name":      {"type": "string",  "label": "Member Name",                    "required": True},
            "fund_name":        {"type": "string",  "label": "Fund Name",                      "required": True},
            "fund_value":       {"type": "decimal", "label": "Fund Credit / Value (ZAR)",      "required": True},
            "retirement_date":  {"type": "date",    "label": "Projected Retirement Date",      "required": False},
            "contributions":    {"type": "decimal", "label": "Annual Contributions (ZAR)",     "required": False},
        },
    },
    {
        "code": "life_insurance_policy",
        "label": "Life Insurance Policy",
        "issuing_authority": "Long-term Insurer",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Long-term Insurance Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 802,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Life insurance policy schedule. "
            "Policyholder name, insurer name, policy number, cover amount, premium, "
            "beneficiaries, commencement date."
        ),
        "extraction_schema": {
            "policyholder_name": {"type": "string",  "label": "Policyholder Name",     "required": True},
            "insurer":           {"type": "string",  "label": "Insurer Name",           "required": True},
            "policy_number":     {"type": "string",  "label": "Policy Number",          "required": True},
            "cover_amount":      {"type": "decimal", "label": "Cover Amount (ZAR)",     "required": True},
            "premium":           {"type": "decimal", "label": "Monthly Premium (ZAR)",  "required": False},
            "beneficiaries":     {"type": "list",    "label": "Beneficiaries",          "required": False},
        },
    },
    {
        "code": "fixed_deposit_certificate",
        "label": "Fixed Deposit Certificate",
        "issuing_authority": "Bank",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Banks Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 803,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Bank fixed deposit certificate. "
            "Depositor name, bank name, deposit amount, interest rate, maturity date, certificate number."
        ),
        "extraction_schema": {
            "depositor_name": {"type": "string",  "label": "Depositor Name",    "required": True},
            "bank_name":      {"type": "string",  "label": "Bank Name",         "required": True},
            "amount":         {"type": "decimal", "label": "Deposit Amount (ZAR)", "required": True},
            "interest_rate":  {"type": "decimal", "label": "Interest Rate (%)", "required": True},
            "maturity_date":  {"type": "date",    "label": "Maturity Date",     "required": True},
        },
    },
    {
        "code": "crypto_proof",
        "label": "Cryptocurrency Proof of Holdings",
        "issuing_authority": "Exchange / Wallet",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Crypto Assets Regulatory Framework (SARB/FSCA)",
        "default_validity_days": 30,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 804,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Cryptocurrency exchange statement or wallet proof of holdings. "
            "Holder name, exchange name, wallet address, asset type (BTC/ETH/etc), balance, date."
        ),
        "extraction_schema": {
            "holder_name":     {"type": "string",  "label": "Holder Name",               "required": True},
            "exchange":        {"type": "string",  "label": "Exchange / Wallet Provider", "required": True},
            "wallet_address":  {"type": "string",  "label": "Wallet Address",            "required": False},
            "asset":           {"type": "string",  "label": "Crypto Asset Type",         "required": True},
            "balance":         {"type": "decimal", "label": "Balance",                   "required": True},
            "date":            {"type": "date",    "label": "Statement Date",            "required": True},
        },
    },

    # ── Asset - Movable (sort_order 900-902) ─────────────────────────────────

    {
        "code": "movable_asset_invoice",
        "label": "Purchase Invoice / Receipt (Movable)",
        "issuing_authority": "Seller / Supplier",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Consumer Protection Act",
        "default_validity_days": None,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 900,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Purchase invoice or receipt for a movable asset. "
            "Item description, serial number, purchase price, seller name, date purchased."
        ),
        "extraction_schema": {
            "item_description": {"type": "text",    "label": "Item Description",   "required": True},
            "purchase_price":   {"type": "decimal", "label": "Purchase Price (ZAR)", "required": True},
            "seller_name":      {"type": "string",  "label": "Seller Name",        "required": True},
            "date_purchased":   {"type": "date",    "label": "Date Purchased",     "required": True},
            "serial_number":    {"type": "string",  "label": "Serial Number",      "required": False},
        },
    },
    {
        "code": "movable_asset_insurance",
        "label": "Movable Asset Insurance Policy",
        "issuing_authority": "Insurer",
        "is_primary_identity_doc": False,
        "regulatory_reference": "Short-term Insurance Act",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 901,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Short-term insurance policy for movable asset (jewellery, art, electronics, etc). "
            "Item description, insurer name, policy number, cover amount, premium."
        ),
        "extraction_schema": {
            "item_description": {"type": "text",    "label": "Item Description",   "required": True},
            "insurer_name":     {"type": "string",  "label": "Insurer Name",       "required": True},
            "policy_number":    {"type": "string",  "label": "Policy Number",      "required": True},
            "cover_amount":     {"type": "decimal", "label": "Cover Amount (ZAR)", "required": True},
            "premium":          {"type": "decimal", "label": "Annual Premium (ZAR)", "required": False},
        },
    },
    {
        "code": "movable_asset_valuation",
        "label": "Movable Asset Valuation Report",
        "issuing_authority": "Appraiser / Valuation Expert",
        "is_primary_identity_doc": False,
        "regulatory_reference": "",
        "default_validity_days": 365,
        "ownership_scope": "owner_bound",
        "applies_to_entity_types": ["asset"],
        "sort_order": 902,
        "email_sender_patterns": [],
        "email_subject_patterns": [],
        "external_reference_codes": [],
        "is_active": True,
        "classification_signals": (
            "Valuation or appraisal report for movable asset (jewellery, art, collectibles, machinery). "
            "Item description, appraised value, appraiser name and credentials, valuation date."
        ),
        "extraction_schema": {
            "item_description": {"type": "text",    "label": "Item Description",   "required": True},
            "appraised_value":  {"type": "decimal", "label": "Appraised Value (ZAR)", "required": True},
            "appraiser_name":   {"type": "string",  "label": "Appraiser Name",     "required": True},
            "valuation_date":   {"type": "date",    "label": "Valuation Date",     "required": True},
        },
    },
]


def seed_forward(apps, schema_editor):
    Catalogue = apps.get_model("the_volt", "DocumentTypeCatalogue")
    for doc in DOCUMENTS:
        doc_copy = doc.copy()
        code = doc_copy.pop("code")
        Catalogue.objects.update_or_create(code=code, defaults=doc_copy)


def seed_reverse(apps, schema_editor):
    Catalogue = apps.get_model("the_volt", "DocumentTypeCatalogue")
    codes = [d["code"] for d in DOCUMENTS]
    Catalogue.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [("the_volt", "0005_seed_document_catalogue")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]

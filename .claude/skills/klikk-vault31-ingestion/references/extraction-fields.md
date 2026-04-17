# Extraction Fields by Document Type

Complete reference for what fields to extract into `extracted_data` during
enrichment. Fields marked with * are identity keys (critical for deduplication).

## Property Transactions

### `otp` — Offer to Purchase

```json
{
  "registration_number": "ERF 3581",          // * asset identity key
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch, 7600",
  "erf_size_m2": 766,
  "title_deed": "T52028/2019",
  "seller": "Otto Business Trust",            // counterparty entity
  "seller_reg": "160/2008",                   // seller identity key
  "seller_trust_numbers": "IT1102/96, IT1099/96",  // for multi-trust sellers
  "seller_contact": "sdotto@sdotto.co.za",
  "seller_cell": "083 657 1587",
  "buyer": "Klikk (Pty) Ltd",                 // counterparty entity
  "buyer_reg": "2016/113758/07",
  "buyer_representative": "MC Dippenaar",
  "buyer_email": "mc@tremly.co.za",
  "purchase_price": 8500000,                  // integer ZAR
  "deposit": 860000,
  "balance": 7650000,
  "bond_amount": 13000000,
  "agent": "Lizanne Fourie",                  // agent person name
  "agent_company": "Pam Golding Properties",  // counterparty entity
  "listing_number": "ST1531367",
  "brokerage_incl_vat": 630000,
  "offer_date": "2022-09-09",                 // ISO date
  "transfer_date": "2017-03-01",              // expected transfer
  "signed_date": "2016-09-15",
  "conveyancers": "Strauss Daly, Bellville",
  "municipality": "Stellenbosch",
  "province": "Western Cape",
  "note": "Price amended from R11M to R13M"   // any special circumstances
}
```

### `transfer_statement` — Transfer Recon / Final Statement

```json
{
  "registration_number": "ERF 3581",
  "property_address": "ERF 3581 Stellenbosch",
  "transfer_from": "Otto Business Trust",     // counterparty entity
  "transfer_to": "Klikk (Pty) Ltd",
  "purchase_price": 8500000,
  "guarantee_received": 7500000,
  "deposit_received": 850000,
  "transfer_costs": 844771.50,
  "interest_received": 10877.88,
  "balance_due_to_purchaser": 10877.88,
  "settlement_date": "2022-12-01",            // = registration_date
  "registration_date": "2022-12-01",
  "attorneys": "Strauss Daly (Western Cape) Incorporated",
  "attorney_ref": "HV/Janine/GCO1/0049",
  "attorney_vat": "482 016 399 8"
}
```

### `title_deed` — Title Deed / Registration Letter

```json
{
  "registration_number": "ERF 3581",
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch",
  "transfer_from": "Otto Business Trust",
  "transfer_to": "Klikk (Pty) Ltd",
  "registration_date": "2022-12-01",
  "attorneys": "Strauss Daly",
  "attorney_ref": "HV/Janine/GCO1/0049"
}
```

### `rental_agreement` — Lease / Huurkontrak

```json
{
  "registration_number": "ERF 3581",
  "property_address": "Otterkuil 2, Karindal, Stellenbosch",
  "landlord": "SD Otto",                      // or "Klikk (Pty) Ltd"
  "managing_agent": "Anna Basson Eiendomme",   // counterparty entity
  "tenant_names": ["Cornelis Schriek"],        // ALWAYS a list
  "tenant_entity": "Schriek Software CC",      // if tenant is a company/CC
  "tenant_reg": "2010/032506/23",              // tenant entity reg number
  "tenant_vat": "4810291759",
  "tenant_id": "8206105285089",                // SA ID of individual tenant
  "monthly_rent_zar": 30000,                   // integer
  "deposit_zar": 45000,
  "lease_start": "2021-09-15",
  "lease_end": "2022-09-30",
  "lease_period_months": 12,
  "max_occupants": 5,
  "signed_date": "2021-06-29",
  "note": "Afrikaans huurkontrak. Lease was in place when Klikk purchased."
}
```

## Property & Municipal

### `municipal_valuation` — Municipal Valuation Roll Entry

```json
{
  "registration_number": "ERF 3581",           // * asset identity key
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch",
  "owner_name": "Klikk (Pty) Ltd",
  "valuation_date": "2023-07-01",
  "market_value": 9500000,
  "municipal_value": 8200000,
  "rates_amount": 12500,
  "erf_size_m2": 766,
  "zoning": "Residential 1",
  "municipality": "Stellenbosch"
}
```

### `levy_clearance` — Body Corporate / HOA Levy Clearance

```json
{
  "registration_number": "ERF 3581",           // * asset identity key
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch",
  "body_corporate": "Karindal Body Corporate",
  "levy_amount_monthly": 2500,
  "arrears": 0,
  "clearance_date": "2022-11-15",
  "clearance_number": "LC-2022-0456"
}
```

### `hoa_rules` — HOA / Body Corporate Conduct Rules

```json
{
  "registration_number": "ERF 3581",           // * asset identity key
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch",
  "body_corporate_name": "Karindal Body Corporate",
  "managing_agent": "PropManage CC",
  "levy_amount": 2500,
  "rules_date": "2020-01-15",
  "scheme_number": "SS123/2005"
}
```

## Certificates of Compliance

### `electrical_coc`

```json
{
  "registration_number": "ERF 3581",
  "property_address": "2 Otterkuil Street, Karindal, Stellenbosch",
  "certificate_number": "ECA M0206016",
  "inspector_name": "Ashwyn Oscar January",
  "inspector_id": "8807055226088",
  "inspector_registration": "IE not specified",
  "contractor_name": "Jean Cilliers",
  "contractor_company": "Cilltec Home Inspections",
  "inspection_date": "2022-11-23",
  "installation_type": "Existing residential"
}
```

### `gas_coc`

```json
{
  "registration_number": "ERF 4087",
  "property_address": "Otterkuil C, Stand No. 4, Stellenbosch",
  "certificate_number": "391388",
  "installer_registration": "2755R",
  "inspection_date": "2017-01-28",
  "owner_at_time": "C Steenkamp",              // counterparty entity
  "gas_stored_kg": 96,
  "installation_standards": "10087-1",
  "appliances": "S Burner Flee, Standing Stove"
}
```

### `beetle_certificate`

```json
{
  "registration_number": "ERF 4087",
  "property_address": "4 Otterkuil Street, Karindal, Stellenbosch",
  "seller": "Callie Steenkamp",
  "inspection_company": "Pest Control Specialists Boland",
  "inspector_name": "Mike Turner",
  "inspector_registration": "0257",
  "inspection_date": "2016-12-08",
  "result": "Clear"                            // Clear or Active infestation
}
```

### `electric_fence_coc`

```json
{
  "registration_number": "ERF 4087",
  "property_address": "4 Otterkuil Street, Stellenbosch",
  "certificate_number": "MTMS 0455",
  "installer_name": "Billy Andre Ackermann",
  "installer_registration": "EFSI01097",
  "inspection_date": "2017-01-25"
}
```

### `building_plans`

```json
{
  "registration_number": "ERF 4087",
  "property_address": "ERF Nr. 4087, Karindal, Stellenbosch",
  "architect": "PG Joubert",
  "drawing_number": "651-2",
  "date": "1965",
  "description": "Proposed New Dwelling for Miss S Potgieter",
  "plans_include": "Ground floor, upper floor, elevations, terrain plan",
  "rooms": "sitkamer, eetkamer, kombuis, 4x slaapkamer, 2x badkamer"
}
```

## Legal / Identity

### `cipc_cor14_3` — Registration Certificate

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "company_type": "Private Company",
  "registration_date": "2016-04-20",
  "directors": ["Michaelis Christoffel Dippenaar"],  // creates relationships
  "registered_address": "40 Froetang Street, Welgevonden, Stellenbosch"
}
```

### `cipc_cor14_1` — Notice of Incorporation (CoR14.1)

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "company_type": "Private Company",
  "incorporation_date": "2016-04-20",
  "directors": ["Michaelis Christoffel Dippenaar"],
  "registered_address": "40 Froetang Street, Welgevonden, Stellenbosch"
}
```

### `cipc_cor14_1a` — Notice of Amendment (CoR14.1A)

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "amendment_type": "Change of directors",
  "amendment_date": "2023-06-15",
  "details": "Removal of director J Smith, appointment of A Jones"
}
```

### `cipc_cor39` — Registered Office Change

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "new_address": "18 Dr Malan Street, La Colline, Stellenbosch",
  "change_date": "2023-03-01"
}
```

### `cipc_disclosure` — CIPC Disclosure Certificate

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "directors": ["Michaelis Christoffel Dippenaar"],
  "shareholders": ["Michaelis Christoffel Dippenaar"],
  "disclosure_date": "2024-01-15"
}
```

### `trust_deed`

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "trust_type": "inter vivos",                 // or "testamentary"
  "deed_date": "1996-05-15",
  "trustees": ["Renee Steenkamp", "Callie Steenkamp"],  // creates relationships
  "beneficiaries": ["Steenkamp Children"],      // creates relationships
  "master_reference": "Ref/1996/123"
}
```

### `letters_of_authority`

```json
{
  "trust_number": "IT1102/96",
  "trust_name": "Renee Steenkamp Familietrust",
  "trustees_authorised": ["Renee Steenkamp", "Callie Steenkamp"],
  "issue_date": "2016-03-15",
  "master_office": "Cape Town"
}
```

### `sa_id_document`

```json
{
  "id_number": "8205315092087",                // * personal identity key
  "full_name": "Michaelis Christoffel Dippenaar",
  "date_of_birth": "1982-05-31",
  "nationality": "South African",
  "gender": "Male"
}
```

### `passport`

```json
{
  "passport_number": "A12345678",              // * personal identity key
  "full_name": "Michaelis Christoffel Dippenaar",
  "nationality": "South African",
  "date_of_birth": "1982-05-31",
  "gender": "Male",
  "issue_date": "2020-03-15",
  "expiry_date": "2030-03-14",
  "place_of_issue": "Pretoria"
}
```

### `drivers_licence` — SA Driver's Licence

```json
{
  "full_name": "Michaelis Christoffel Dippenaar",
  "id_number": "8205315092087",                // * personal identity key
  "licence_number": "DL12345678",
  "code": "B",
  "restrictions": "None",
  "issue_date": "2005-06-01",
  "expiry_date": "2030-05-31"
}
```

### `proof_of_address` — FICA Proof of Address

```json
{
  "full_name": "Michaelis Christoffel Dippenaar",
  "id_number": "8205315092087",                // * personal identity key
  "physical_address": "18 Dr Malan Street, La Colline, Stellenbosch, 7600",
  "postal_address": "PO Box 123, Stellenbosch, 7599",
  "date": "2024-01-15",
  "document_source": "Municipal account",      // "Municipal account", "Bank statement", "Signed declaration"
  "municipality": "Stellenbosch"
}
```

### `marriage_certificate`

```json
{
  "spouse_names": [                            // ALWAYS a list of 2
    "Michaelis Christoffel Dippenaar",
    "Stefanie Viljoen"
  ],
  "date_of_marriage": "2010-03-20",
  "place_of_marriage": "Stellenbosch",
  "regime": "ANC with accrual",               // or "COP", "ANC without accrual"
  "marriage_officer": "Rev. J van der Merwe"
}
```

### `antenuptial_contract`

```json
{
  "parties": [
    "Michaelis Christoffel Dippenaar (ID 8205315092087)",
    "Stefanie Viljoen (ID 8701180125085)"
  ],
  "registration_number": "ANC/2010/1234",
  "accrual_system": true,
  "notary": "J. Smith Notary",
  "date": "2010-03-15"
}
```

### `divorce_order` — Court Divorce Order

```json
{
  "case_number": "2023/12345",
  "court": "Western Cape High Court",
  "plaintiff": "Stefanie Dippenaar",
  "defendant": "Michaelis Christoffel Dippenaar",
  "plaintiff_id": "8701180125085",
  "defendant_id": "8205315092087",
  "date_of_order": "2024-06-15",
  "date_of_divorce": "2024-06-15",
  "custody_arrangement": "Shared custody",
  "asset_division_notes": "Accrual claim settled per agreement"
}
```

### `will` — Last Will and Testament

```json
{
  "testator_name": "Michaelis Christoffel Dippenaar",
  "testator_id": "8205315092087",              // * personal identity key
  "executor_name": "First National Trust",
  "executor_id": "1920/000123/06",
  "date_signed": "2022-01-10",
  "witnesses": ["Jan de Villiers", "Anna Botha"],
  "beneficiaries": ["Stefanie Dippenaar", "Dippenaar Family Trust"],
  "specific_bequests": ["ERF 3581 to Dippenaar Family Trust"],
  "residue_heir": "Stefanie Dippenaar"
}
```

### `medical_certificate`

```json
{
  "patient_name": "Michaelis Christoffel Dippenaar",
  "patient_id": "8205315092087",               // * personal identity key
  "practitioner_name": "Dr J van Niekerk",
  "practice_number": "MP0123456",
  "date": "2024-03-01",
  "diagnosis_summary": "Upper respiratory tract infection",
  "fitness_status": "Unfit for 3 days"
}
```

### `share_certificate`

```json
{
  "reg_number": "2016/113758/07",
  "company_name": "Klikk (Pty) Ltd",
  "shareholder_name": "Michaelis Christoffel Dippenaar",
  "shares": 100,
  "share_class": "Ordinary",
  "certificate_number": "001",
  "issue_date": "2016-04-20"
}
```

## Company / Corporate

### `directors_resolution` — Board Resolution

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "resolution_date": "2024-01-15",
  "resolution_type": "Ordinary",
  "directors_present": ["Michaelis Christoffel Dippenaar"],
  "resolution_text_summary": "Approval to purchase ERF 5012, Stellenbosch for R6,500,000",
  "signed_by": "Michaelis Christoffel Dippenaar"
}
```

### `shareholder_resolution` — Shareholder Resolution

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "resolution_date": "2024-01-15",
  "resolution_type": "Special",
  "shareholders_present": ["Michaelis Christoffel Dippenaar"],
  "resolution_text_summary": "Approval of MOI amendment to increase authorised shares"
}
```

### `moi` — Memorandum of Incorporation

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "company_type": "Private Company",
  "incorporation_date": "2016-04-20",
  "authorized_shares": 1000,
  "directors": ["Michaelis Christoffel Dippenaar"],
  "registered_address": "40 Froetang Street, Welgevonden, Stellenbosch",
  "financial_year_end": "2024-02-28",
  "special_conditions": "None"
}
```

### `securities_register` — Company Securities Register

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "shareholders": [
    {
      "name": "Michaelis Christoffel Dippenaar",
      "id_number": "8205315092087",
      "shares": 100,
      "share_class": "Ordinary",
      "date_acquired": "2016-04-20"
    }
  ]
}
```

### `bo_register` — Beneficial Ownership Register

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "beneficial_owners": [
    {
      "name": "Michaelis Christoffel Dippenaar",
      "id_number": "8205315092087",
      "percentage": 100,
      "nature_of_interest": "Direct shareholding"
    }
  ]
}
```

### `company_bank_confirmation` — Bank Confirmation Letter (Company)

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "bank_name": "First National Bank",
  "account_number": "62812345678",
  "branch_code": "250655",
  "account_type": "Business Cheque Account",
  "confirmation_date": "2024-01-10"
}
```

### `vat_registration` — VAT Registration Certificate

```json
{
  "reg_number": "2016/113758/07",              // * company identity key
  "company_name": "Klikk (Pty) Ltd",
  "vat_number": "4123456789",
  "registration_date": "2017-01-01",
  "tax_period": "Category A - bi-monthly"
}
```

## Trust

### `trust_resolution` — Trustees Meeting Minutes / Resolution

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "resolution_date": "2024-01-15",
  "trustees_present": ["Renee Steenkamp", "Callie Steenkamp"],
  "resolution_summary": "Approval to sell ERF 4087, Stellenbosch for R5,200,000",
  "signed_by": "Renee Steenkamp"
}
```

### `trust_amendment_deed` — Amendment to Trust Deed

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "amendment_date": "2023-06-01",
  "amendment_summary": "Addition of new trustee: Jan Steenkamp",
  "registered_at_master": true
}
```

### `trust_bank_confirmation` — Bank Confirmation Letter (Trust)

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "bank_name": "ABSA Bank",
  "account_number": "40712345678",
  "branch_code": "632005",
  "account_type": "Trust Current Account",
  "confirmation_date": "2024-02-01"
}
```

### `trust_tax_clearance` — Tax Clearance (Trust)

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "tax_number": "9012345678",
  "clearance_date": "2024-03-01",
  "tax_year": "2023",
  "status": "Good standing"
}
```

### `trust_financial_statements` — Trust Financial Statements

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "financial_year_end": "2024-02-28",
  "net_income": 450000,
  "total_assets": 12000000,
  "auditor": "Moore Stellenbosch"
}
```

### `beneficiary_list` — Schedule of Trust Beneficiaries

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "beneficiaries": [
    {
      "name": "Jan Steenkamp",
      "id_number": "0501015092088",
      "category": "Income",
      "share_percentage": 50
    },
    {
      "name": "Anna Steenkamp",
      "id_number": "0801015092089",
      "category": "Income",
      "share_percentage": 50
    }
  ]
}
```

### `master_correspondence` — Master of the High Court Letters

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "master_office": "Cape Town",
  "reference_number": "MT/2024/0456",
  "date": "2024-02-15",
  "subject": "Confirmation of trustee appointment",
  "correspondence_type": "Confirmation"
}
```

### `trustee_id_copies` — Certified ID Copies for Trustees

```json
{
  "trust_number": "IT1102/96",                 // * trust identity key
  "trust_name": "Renee Steenkamp Familietrust",
  "trustee_name": "Callie Steenkamp",
  "trustee_id": "5601015092086",
  "certification_date": "2024-01-05"
}
```

## Financial

### `bond_statement` — Bond Facility / Advice of Grant

```json
{
  "registration_number": "ERF 2689",
  "bank_name": "Investec Private Bank",
  "account_number": "10011924075",
  "branch_code": "580105",
  "facility_amount": 5500000,
  "interest_rate": "prime minus 0.25%",
  "term_months": 240,
  "approval_date": "2018-06-15"
}
```

### `financial_statements`

```json
{
  "entity_name": "Klikk (Pty) Ltd",
  "reg_number": "2016/113758/07",
  "financial_year_end": "2023-02-28",
  "net_income": 1770883,
  "total_assets": 25000000,
  "auditor": "Moore Stellenbosch",
  "auditor_registration": "IRBA 123456"
}
```

### `property_insurance`

```json
{
  "registration_number": "ERF 2689",
  "property_address": "18 Dr Malan Street, La Colline",
  "insurer": "Santam",
  "policy_number": "POL123456",
  "sum_insured": 3500000,
  "premium_monthly": 1250,
  "cover_type": "Building and contents",
  "effective_date": "2023-01-01",
  "expiry_date": "2024-01-01"
}
```

### `bank_confirmation_letter` — Generic Bank Confirmation

```json
{
  "account_holder": "Michaelis Christoffel Dippenaar",
  "bank_name": "First National Bank",
  "account_number": "62812345678",
  "branch_code": "250655",
  "account_type": "Cheque Account",
  "confirmation_date": "2024-01-10"
}
```

### `sars_itr` — SARS Income Tax Return

```json
{
  "taxpayer_name": "Michaelis Christoffel Dippenaar",
  "tax_number": "1234567890",
  "tax_year": "2023",
  "taxable_income": 1250000,
  "tax_payable": 387500,
  "refund_amount": 0
}
```

## Notes

- All date fields use ISO format: `"2022-09-09"`
- All money fields are integers in ZAR (no cents): `8500000`
- Lists always use array syntax even for single items: `["Name"]`
- Include `note` field for anything unusual (misfiling, Afrikaans, partial data)
- `owner_at_time` creates a `sold_to` relationship (previous owner of asset)
- Multi-trust sellers should use `&` separator in `seller` field AND provide
  individual trust numbers in `seller_trust_numbers` (comma-separated)
- When extracting from `proof_of_address` documents, ALWAYS propagate the
  address to the parent entity's `data.address` field. This is critical for
  FICA compliance -- the vault must know current addresses.

# CIPC / CIPRO Document Taxonomy

## Overview

The Companies and Intellectual Property Commission (CIPC) is the South African body that registers companies, close corporations, co-operatives, and intellectual property rights. All CoR (Company Registration) forms are issued or filed with CIPC.

**Registration number formats:**
- `YYYY/XXXXXX/07` — Private company (Pty Ltd)
- `YYYY/XXXXXX/06` — Public company (Ltd)
- `YYYY/XXXXXX/08` — Close Corporation (CC) — legacy
- `YYYY/XXXXXX/10` — External company
- `YYYY/XXXXXX/21` — Non-Profit Company (NPC)
- `YYYY/XXXXXX/23` — State-owned company (SOC Ltd)
- `ITxxxx/YYYY` — Trust (registered with Master of High Court)
- `CKxxxxxxx/xx` — Close Corporation founding number

---

## Table of Contents

1. [Company Forms (CoR)](#company-forms)
2. [Close Corporation Forms (CK)](#cc-forms)
3. [Trust Documents](#trust-documents)
4. [Partnership Documents](#partnership-documents)
5. [SARS / Tax Documents](#sars-documents)
6. [Extraction Field Schemas](#extraction-schemas)

---

## 1. Company Forms (CoR) {#company-forms}

### CoR9.1 — Name Application
- Filed to reserve a company name
- Contains: proposed name, applicant details, date

### CoR9.4 — Name Approval
- Confirms name reservation (valid 6 months)
- Extract: reserved_name, reservation_date, expiry_date

### CoR14.1 — Application for Company Registration
- Filed at incorporation
- Extract: proposed_company_name, share_capital, initial_directors[], shareholders[], registered_address

### CoR14.3 — Registration Certificate ⭐ PRIMARY IDENTITY DOCUMENT
- The official proof of incorporation, issued by CIPC
- **Key classification signal:** CIPC logo, "Certificate of Incorporation", or "Registration Certificate" heading
- Extract:
  - `registration_number` (YYYY/XXXXXX/07)
  - `company_name` (including legal suffix)
  - `entity_type` — derived from suffix: "(Pty) Ltd" | "NPC" | "SOC Ltd" | "Ltd"
  - `registration_date`
  - `registered_address`
  - `cipc_status` — look for "Active" or "Deregistered" stamp/watermark
  - `registrar_reference` — unique verification code (bottom of document)

### CoR15.1A — Standard Memorandum of Incorporation (MOI) for Private Companies
- Applies to: Pty Ltd, SOC Ltd
- Governs internal company rules
- **Key classification signal:** "Memorandum of Incorporation", "MOI", CoR15 header
- Extract:
  - `company_name`
  - `share_structure` (classes, number of shares)
  - `profit_distribution_allowed` (true for Pty Ltd, false for NPC)
  - `amendment_date`
  - `non_profit_clauses_present` (true for NPC — look for "no distribution to members/directors")

### CoR15.1B — Altered / Long-form MOI
- Custom MOI deviating from standard
- Same extraction schema as CoR15.1A

### CoR15.1C/D/E — MOI Variants
- Same extraction schema as CoR15.1A

### CoR16.1 — Share/Membership Amendment
- Tracks share class or membership changes

### CoR20.1 — Secretary Appointment / Change
- Extract: secretary_name, appointment_date

### CoR21.1 — Notice of Change of Registered Office
- **Key classification signal:** "Registered Office", "Notice of Change of Address"
- Extract: new_registered_address, effective_date

### CoR22 — Share Allotment
- Records new share issuance

### CoR25 — Director Resignation
- Extract: director_name, id_number, resignation_date

### CoR39 — Notice of Directors ⭐ CURRENT DIRECTORS
- Filed when directors are appointed or removed
- **Key classification signal:** "CoR39", "Notice of Directors", "Director Consent"
- Extract:
  - `directors[]`:
    - `full_name`
    - `id_number` (SA ID, 13 digits) or `passport_number`
    - `nationality`
    - `appointed_date`
    - `designation` (Director / Managing Director / Non-Executive, etc.)
    - `residential_address`
  - `company_name`
  - `registration_number`
  - `filing_date`

### CoR40.1 — Special Resolution to Wind-up Solvent Company
- **Key classification signal:** "Winding-up", "Voluntary Liquidation", "Dissolution"
- Extract: resolution_date, effective_date
- **Red flag:** If present → company is being dissolved

### CoR123.1 / CoR123.2 / CoR123.3 — Annual Return
- Filed annually with CIPC; confirms the company is still active
- **Key classification signal:** "Annual Return", "CoR123"
- Extract: filing_year, filing_date, company_name, registration_number
- **Red flag if absent:** Company registered > 1 year ago and no annual return found

---

## 2. Close Corporation Forms (CK) {#cc-forms}

Close Corporations were registered under the Close Corporations Act 69 of 1984. No new CCs may be registered (since 2011), but existing CCs remain valid legal entities.

### CK1 — Founding Statement ⭐ PRIMARY CC IDENTITY DOCUMENT
- Original registration document for a CC
- **Key classification signal:** "CK1", "Founding Statement", "CC" suffix, "CK" number format
- Extract:
  - `cc_name`
  - `ck_number` (format: CKxxxxxxx/xx)
  - `registration_date`
  - `members[]`:
    - `full_name`
    - `id_number`
    - `interest_percentage` (sum must = 100%)
    - `contribution`
  - `accounting_officer` (name + practice number)
  - `business_address`
  - `nature_of_business`

### CK2 — Amended Founding Statement
- Filed for any change: new member, address, name, member interest
- **Key classification signal:** "CK2", "Amended Founding Statement"
- Extract same fields as CK1 plus:
  - `amendment_date`
  - `amendment_description`

### CK2A — Accounting Officer and Address Amendment
- Specific subset of CK2 for accounting officer changes and address changes only
- Extract: new_accounting_officer, new_address, effective_date

---

## 3. Trust Documents {#trust-documents}

Trusts are **not** registered with CIPC. They are registered with the **Master of the High Court** (Department of Justice and Constitutional Development).

### Trust Deed (Inter Vivos Trust)
- The founding legal document of the trust
- **Key classification signal:** "Trust Deed", "Deed of Trust", "inter vivos", founding clauses, trustee appointment clauses
- Extract:
  - `trust_name`
  - `trust_number` (format: ITxxxx/YYYY)
  - `founding_date`
  - `trustees[]`:
    - `full_name`
    - `id_number`
  - `beneficiaries[]` (if named):
    - `full_name`
    - `id_number` (if natural person)
    - `benefit_description`
  - `trust_objectives`
  - `asset_distribution_rules`

### Letters of Authority (Master of the High Court) ⭐ TRUST VERIFICATION DOCUMENT
- Issued by the Master of the High Court upon acceptance of the trust deed
- Authorises named trustees to act as trustees
- **Key classification signal:** "Master of the High Court", "Letters of Authority", "I hereby authorise", "URN", official government seal
- Extract:
  - `trust_name`
  - `trust_number` (format: ITxxxx/YYYY)
  - `urn` (Unique Reference Number — bottom left of document)
  - `trustees[]`:
    - `full_name`
    - `id_number`
  - `issued_by`: always "Master of the High Court"
  - `master_office` (e.g. "Pretoria", "Cape Town")
  - `issue_date`
- **Critical check:** The trustees listed on the Letter of Authority must match the ID copies provided for FICA

---

## 4. Partnership Documents {#partnership-documents}

Partnerships are not registered with CIPC. They are governed by a contract between the partners.

### Partnership Agreement
- The founding contract of the partnership
- **Key classification signal:** "Partnership Agreement", "Joint Venture Agreement", partner names and profit-sharing clauses
- Extract:
  - `partnership_name`
  - `commencement_date`
  - `partners[]`:
    - `full_name`
    - `id_number`
    - `profit_share_percentage` (sum must = 100%)
    - `capital_contribution`
  - `business_address`
  - `nature_of_business`
  - `duration` (if fixed term)

---

## 5. SARS / Tax Documents {#sars-documents}

### SARS Income Tax Registration
- **Key classification signal:** "South African Revenue Service", "SARS", "Income Tax Reference Number", "IT Number"
- Extract:
  - `entity_name`
  - `tax_number` (10 digits, starts with 0, 1, 2, or 3)
  - `registration_date`

### SARS VAT Registration
- **Key classification signal:** "VAT Registration", "VAT Number", "Value Added Tax"
- Extract:
  - `entity_name`
  - `vat_number` (10 digits, starts with 4)
  - `effective_date`

### SARS Tax Clearance Certificate (Good Standing)
- **Key classification signal:** "Tax Clearance Certificate", "Good Standing", "PIN"
- Extract:
  - `entity_name`
  - `tax_number`
  - `pin` (for online verification)
  - `valid_until`

---

## 6. Extraction Field Schemas {#extraction-schemas}

### Standard company document extraction

```json
{
  "document_code": "CoR14.3",
  "document_name": "Registration Certificate",
  "bucket": "CIPC",
  "registration_number": "2018/123456/07",
  "company_name": "Acme Property (Pty) Ltd",
  "entity_type": "Pty Ltd",
  "registration_date": "2018-03-15",
  "registered_address": "12 Oak Street, Stellenbosch, 7600",
  "cipc_status": "Active",
  "registrar_reference": "ABC123456"
}
```

### Director extraction (CoR39)

```json
{
  "document_code": "CoR39",
  "document_name": "Notice of Directors",
  "bucket": "CIPC",
  "company_name": "Acme Property (Pty) Ltd",
  "registration_number": "2018/123456/07",
  "filing_date": "2018-03-15",
  "directors": [
    {
      "full_name": "John Smith",
      "id_number": "7601015009087",
      "nationality": "South African",
      "appointed_date": "2018-03-15",
      "designation": "Director"
    }
  ]
}
```

### Trust Letter of Authority extraction

```json
{
  "document_code": "LetterOfAuthority",
  "document_name": "Letters of Authority",
  "bucket": "CIPC",
  "trust_name": "Smith Family Trust",
  "trust_number": "IT1234/2015",
  "urn": "12345/2015",
  "issued_by": "Master of the High Court",
  "master_office": "Cape Town",
  "issue_date": "2015-07-01",
  "trustees": [
    {"full_name": "Jane Smith", "id_number": "7812020012089"}
  ]
}
```

### CC Founding Statement extraction (CK1)

```json
{
  "document_code": "CK1",
  "document_name": "CC Founding Statement",
  "bucket": "CIPC",
  "cc_name": "Smith Builders CC",
  "ck_number": "CK2005/012345/23",
  "registration_date": "2005-06-10",
  "members": [
    {
      "full_name": "John Smith",
      "id_number": "7601015009087",
      "interest_percentage": "60",
      "contribution": "R60,000"
    },
    {
      "full_name": "Mary Jones",
      "id_number": "8203080045084",
      "interest_percentage": "40",
      "contribution": "R40,000"
    }
  ],
  "accounting_officer": "ABC Accounting (Practice No. 12345)",
  "business_address": "45 Main Road, Paarl, 7646"
}
```

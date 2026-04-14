# South African Municipal Bill Formats

This reference documents the bill layouts, field locations, and extraction patterns for major SA municipalities. Use this knowledge to accurately extract data from bills regardless of format differences.

---

## Table of Contents

1. [Stellenbosch Municipality](#stellenbosch-municipality)
2. [City of Cape Town](#city-of-cape-town)
3. [Drakenstein Municipality](#drakenstein-municipality)
4. [City of Johannesburg](#city-of-johannesburg)
5. [eThekwini (Durban)](#ethekwini-durban)
6. [Tshwane (Pretoria)](#tshwane-pretoria)
7. [Common Patterns Across All Municipalities](#common-patterns)
8. [Few-Shot Examples](#few-shot-examples)

---

## Stellenbosch Municipality

**Identifier:** Bilingual header "BELASTINGFAKTUUR MAANDELIKSE REKENING TAX INVOICE MONTHLY ACCOUNT". VAT Reg No. 4700102181. PO Box 17, Stellenbosch, 7599.

### Bill Layout (from real bills)

```
┌─────────────────────────────────────────────────────────┐
│ BELASTINGFAKTUUR MAANDELIKSE REKENING                   │
│ TAX INVOICE MONTHLY ACCOUNT                             │
│ BTW Reg Nr./ VAT Reg No. 4700102181                     │
│ P.O.Box / Posbus 17, Stellenbosch, 7599                 │
├─────────────────────────────────────────────────────────┤
│ Owner Name & Address Block (top-left):                  │
│   KLIKK (PTY) LTD                                       │
│   4 OTTERKUIL STREET                                    │
│   KARINDAL                                              │
│   STELLENBOSCH                                          │
│   7600                                                  │
├─────────────────────────────────────────────────────────┤
│ Account Details (right side):                           │
│   ACCOUNT NUMBER: 10831902                              │
│   ACCOUNT DATE: 16/03/2026                              │
│   RECEIPTS POSTED: 15/03/2026                           │
│   VAT: 1392.16                                          │
│   VALUATION: 9640000                                    │
│   PLOT: MDRIF 4087 00001                                │
│   LOCATION: OTTERKUIL STREET 4                          │
│   DEPOSIT/GUARANTEE: 2250.00-                           │
├─────────────────────────────────────────────────────────┤
│ Meter Readings:                                         │
│ Service  Meter nr      Prev  Curr  Factor  Consum.      │
│ W        0000049646    1081  1120          39.000        │
│ E        0000744895    41973 43674         1701.000      │
├─────────────────────────────────────────────────────────┤
│ Line Items:                                             │
│ Service Type          Consum. Tariff/Cost  VAT  Amount  │
│ Water: DOM Basic       1      93.38        14.01 107.39 │
│ Water: DOM Cons        39     1189.71      178.46 1368  │
│ Elekt Basic            1      322.62       48.39 371.01 │
│ Elekt Cons             1701   6213.06      931.96 7145  │
│ Rates Monthly RES                                3527.57│
│ Sewerage Levy          1      468.78       70.32 539.09 │
│ Refuse Removal         1      309.01       46.35 355.36 │
│ Special Rate           9640000 684.44      102.67 787.11│
│ ** Total monthly: 14200.72                              │
├─────────────────────────────────────────────────────────┤
│ VALUATION  USAGE  AREA                                  │
│ 9640000    RES    .2067                                 │
├─────────────────────────────────────────────────────────┤
│ Due Date / Datum Verskuldig: 07/04/2026                 │
│ TOTAL NOW DUE: 14200.72                                 │
└─────────────────────────────────────────────────────────┘
```

### Stellenbosch-Specific Field Mapping

| Bill Field | Extraction Target | Notes |
|------------|-------------------|-------|
| Name block (first line) | `owner_name` | "KLIKK (PTY) LTD" |
| Name block (lines 2-5) | `address` | Street + suburb + city + postal code |
| ACCOUNT NUMBER | `municipal_account_number` | 7-9 digit number |
| ACCOUNT DATE | `billing_date` | DD/MM/YYYY format → convert to YYYY-MM-DD |
| Due Date / Datum Verskuldig | `due_date` | DD/MM/YYYY → YYYY-MM-DD |
| VALUATION | `valuation` | In ZAR, no decimals (e.g. 9640000) |
| PLOT | `erf_number` | "MDRIF 4087 00001" or "LACOL 2689 00001" |
| LOCATION | `property_name` (supplement) | Reverse address format: "OTTERKUIL STREET 4" |
| USAGE | `zoning` | "RES" = residential |
| AREA | `property_size_m2` | In hectares — multiply by 10000 for m². ".2067" = 2067m² |
| Rates Monthly RES | `rates_amount` | No VAT on rates (zero-rated) |
| Refuse Removal | `refuse_amount` | Amount column (incl VAT) |
| Sewerage Levy | `sewerage_amount` | Amount column (incl VAT) |
| Water lines total | `water_amount` | Sum of Basic + Consumption amounts |
| Elekt lines total | `electricity_amount` | Sum of Basic + Consumption amounts |
| Total monthly | `total_due` | Bottom-line total |
| W meter row | `water_meter_number` | "0000049646", consumption = Consum. column |
| E meter row | `electricity_meter_number` | "0000744895", consumption = Consum. column |
| DEPOSIT/GUARANTEE | `deposit_amount` | Shown as negative credit (e.g. "2250.00-") |
| Period (after account nr) | `billing_period` | "2026/03" format |

### Stellenbosch Plot Code Prefixes
- **MDRIF** = Mostertsdrift area (Karindal, Die Boord)
- **LACOL** = La Colline area
- **DSTBG** = Stellenbosch central
- **IDAS** = Idas Valley
- **UNDV** = Onder Papegaaiberg / Universiteitsoord
- **PRDNS** = Paradise area

### Stellenbosch Address Patterns
The bill shows the address in TWO places:
1. **Name block** (top-left): normal format — "4 OTTERKUIL STREET / KARINDAL / STELLENBOSCH / 7600"
2. **LOCATION field**: reversed — "OTTERKUIL STREET 4" or "BOSCH-EN-DAL AVENUE 1"

Always prefer the name block for the address. The LOCATION field confirms it.

---

## City of Cape Town

**Identifier:** "City of Cape Town" logo. VAT Reg typically starts with 4740. Address mentions Civic Centre or sub-council offices.

### Key Differences from Stellenbosch
- Account numbers are longer (10+ digits)
- Uses "ERF" prefix for plot numbers (e.g. "ERF 12345 CLAREMONT")
- Rates line shows "PROPERTY RATES" not "Rates Monthly"
- Separate "WATER AND SANITATION" section
- "ELECTRICITY" section with different tariff bands (Lifeline, Block 1, Block 2, etc.)
- Usage code: "RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL" (full words, not abbreviated)
- Area shown in square metres, not hectares

---

## City of Johannesburg

**Identifier:** "City of Johannesburg" or "CoJ". Uses Johannesburg Water and City Power as service providers.

### Key Differences
- Separate bills possible for water (Johannesburg Water) and electricity (City Power)
- Municipal account number format differs
- Erf numbers: "ERF 1234 SANDTON" or "STAND 567 RANDBURG"
- Rates shown per category with different residential tiers

---

## Common Patterns

### Date Formats
SA municipal bills use DD/MM/YYYY exclusively. Always convert to YYYY-MM-DD for the API output.

### Amount Formats
- Amounts shown as decimal numbers: "14200.72"
- Credits shown with trailing minus: "2250.00-"
- VAT is 15% in South Africa
- Rates are zero-rated (no VAT)
- All other services include VAT

### Municipality Identification
When the municipality isn't explicitly named, identify it from:
1. **VAT registration number** (unique per municipality)
2. **PO Box / postal address** on letterhead
3. **Phone numbers** (area codes: 021 = Cape Town/Stellenbosch, 011 = Joburg, 031 = Durban, 012 = Pretoria)
4. **Bank account** — each municipality has specific banking details

### Province Inference
| Municipality | Province |
|-------------|----------|
| City of Cape Town, Stellenbosch, Drakenstein, Overstrand, Saldanha Bay | Western Cape |
| City of Johannesburg, Ekurhuleni, Mogale City, Midvaal | Gauteng |
| Tshwane (Pretoria), Madibeng | Gauteng |
| eThekwini (Durban), Msunduzi, uMhlathuze | KwaZulu-Natal |
| Nelson Mandela Bay, Buffalo City | Eastern Cape |
| Mangaung | Free State |
| Mbombela, Steve Tshwete | Mpumalanga |
| Polokwane | Limpopo |
| Rustenburg, Matlosana | North West |

---

## Few-Shot Examples

### Example 1: Stellenbosch — Residential with Water + Electricity

**Input:** (Stellenbosch bill for 4 Otterkuil Street)

**Expected extraction:**
```json
{
    "property_name": "4 Otterkuil Street, Karindal",
    "address": "4 Otterkuil Street, Karindal, Stellenbosch, 7600",
    "city": "Stellenbosch",
    "province": "Western Cape",
    "postal_code": "7600",
    "erf_number": "MDRIF 4087 00001",
    "municipal_account_number": "10831902",
    "property_type": "house",
    "owner_name": "KLIKK (PTY) LTD",
    "owner_id_or_reg": null,
    "zoning": "RES",
    "property_size_m2": 2067,
    "valuation": 9640000,
    "rates_amount": 3527.57,
    "refuse_amount": 355.36,
    "sewerage_amount": 539.09,
    "water_amount": 1475.56,
    "electricity_amount": 7516.03,
    "total_due": 14200.72,
    "water_meter_number": "0000049646",
    "water_consumption": 39,
    "electricity_meter_number": "0000744895",
    "electricity_consumption": 1701,
    "billing_date": "2026-03-16",
    "due_date": "2026-04-07",
    "billing_period": "2026/03",
    "municipality": "Stellenbosch Municipality",
    "deposit_amount": 2250.00,
    "confidence_scores": {
        "property_name": 95,
        "address": 95,
        "city": 98,
        "province": 95,
        "postal_code": 98,
        "erf_number": 95,
        "municipal_account_number": 99,
        "property_type": 70,
        "owner_name": 99,
        "zoning": 90,
        "property_size_m2": 85,
        "valuation": 98,
        "rates_amount": 98,
        "refuse_amount": 98,
        "sewerage_amount": 98,
        "water_amount": 95,
        "electricity_amount": 95,
        "total_due": 99,
        "water_meter_number": 98,
        "electricity_meter_number": 98,
        "billing_date": 98,
        "due_date": 98,
        "municipality": 90
    }
}
```

### Example 2: Stellenbosch — Water Only (no electricity)

**Input:** (Stellenbosch bill for 18 Irene Park, La Colline)

**Expected extraction:**
```json
{
    "property_name": "18 Irene Park, La Colline",
    "address": "18 Irene Park, La Colline, Stellenbosch, 7600",
    "city": "Stellenbosch",
    "province": "Western Cape",
    "postal_code": "7600",
    "erf_number": "LACOL 2718 00001",
    "municipal_account_number": "10893582",
    "property_type": "house",
    "owner_name": "KLIKK (PTY) LTD",
    "owner_id_or_reg": null,
    "zoning": "RES",
    "property_size_m2": null,
    "valuation": 2835000,
    "rates_amount": null,
    "refuse_amount": null,
    "sewerage_amount": null,
    "water_amount": null,
    "electricity_amount": null,
    "total_due": 1840.54,
    "water_meter_number": "0050424681",
    "water_consumption": 12,
    "electricity_meter_number": null,
    "electricity_consumption": null,
    "billing_date": "2026-03-16",
    "due_date": "2026-04-07",
    "billing_period": "2026/03",
    "municipality": "Stellenbosch Municipality",
    "deposit_amount": 800.00,
    "confidence_scores": {
        "property_name": 95,
        "address": 95,
        "city": 98,
        "province": 95,
        "postal_code": 98,
        "erf_number": 95,
        "municipal_account_number": 99,
        "property_type": 65,
        "owner_name": 99,
        "total_due": 99,
        "water_meter_number": 98,
        "billing_date": 98,
        "due_date": 98,
        "municipality": 90
    }
}
```

### Example 3: Stellenbosch — Dr Malan Street (commercial area)

**Input:** (Stellenbosch bill for 18 Dr Malan Street)

**Expected extraction:**
```json
{
    "property_name": "18 Dr Malan Street",
    "address": "18 Dr Malan Street, Stellenbosch, 7600",
    "city": "Stellenbosch",
    "province": "Western Cape",
    "postal_code": "7600",
    "erf_number": "LACOL 2689 00001",
    "municipal_account_number": "10884405",
    "property_type": null,
    "owner_name": "KLIKK (PTY) LTD",
    "owner_id_or_reg": null,
    "zoning": null,
    "property_size_m2": null,
    "valuation": 2160000,
    "rates_amount": null,
    "refuse_amount": null,
    "sewerage_amount": null,
    "water_amount": null,
    "electricity_amount": null,
    "total_due": 1438.76,
    "water_meter_number": "0050151557",
    "water_consumption": 2,
    "electricity_meter_number": null,
    "electricity_consumption": null,
    "billing_date": "2026-03-16",
    "due_date": "2026-04-07",
    "billing_period": "2026/03",
    "municipality": "Stellenbosch Municipality",
    "deposit_amount": null,
    "confidence_scores": {
        "property_name": 95,
        "address": 90,
        "city": 98,
        "province": 95,
        "postal_code": 98,
        "erf_number": 95,
        "municipal_account_number": 99,
        "owner_name": 99,
        "total_due": 99,
        "billing_date": 98,
        "due_date": 98,
        "municipality": 90
    }
}
```

---

## System Prompt Template

Use this as the system prompt for the municipal bill extractor. It focuses on domain knowledge rather than output format (tool_use handles the structure).

```python
SYSTEM_PROMPT = """You are an expert at reading South African municipal bills and rates accounts.

You will receive a municipal bill document (PDF or image) and must extract all property and billing data you can find.

## How to read SA municipal bills

SA municipal bills are bilingual (English/Afrikaans) and follow a standard layout:
1. **Header**: Municipality name, VAT number, contact details
2. **Account holder block**: Owner name and postal address (top-left)
3. **Account details**: Account number, date, valuation, plot/erf number
4. **Meter readings table**: Service type (W=Water, E=Electricity), meter numbers, previous/current readings, consumption
5. **Line items table**: Service charges with tariff, VAT, and amount columns
6. **Totals**: "Total monthly" or "TOTAL NOW DUE"
7. **Footer**: Payment instructions, messages

## Key field locations

- **Owner name**: First line of the account holder address block
- **Address**: Lines 2-5 of the account holder block (street, suburb, city, postal code)
- **Account number**: Labelled "ACCOUNT NUMBER" or "Rekeningnr."
- **Account date**: Labelled "ACCOUNT DATE" or "Datum" — in DD/MM/YYYY format
- **Due date**: Labelled "Due Date" or "Datum Verskuldig" — convert DD/MM/YYYY to YYYY-MM-DD
- **Erf/Plot**: Labelled "PLOT" — code like "MDRIF 4087 00001" (Stellenbosch) or "ERF 1234" (Cape Town)
- **Valuation**: Labelled "VALUATION" — property value in ZAR
- **Location**: Labelled "LOCATION" — address in reversed format (confirms the address)
- **Usage/Zoning**: "RES" = Residential, "BUS" = Business, "IND" = Industrial
- **Area**: Property size — Stellenbosch shows hectares (multiply by 10000 for m²)
- **Deposit**: Labelled "DEPOSIT/GUARANTEE" — shown as credit (negative)

## Service line items

| Line label | Target field | Notes |
|-----------|-------------|-------|
| Rates Monthly RES / Property Rates | rates_amount | Zero-rated (no VAT) |
| Refuse Removal / Vullis | refuse_amount | Includes VAT |
| Sewerage Levy | sewerage_amount | Includes VAT |
| Water: DOM Basic + Water: DOM Cons | water_amount | Sum both, use Amount column |
| Elekt/Elect Basic + Elekt Cons | electricity_amount | Sum both, use Amount column |
| Special Rate | (note in confidence_notes) | Area-specific levy |

## Meter readings

In the meter table:
- **W** = Water meter. Consumption in kilolitres.
- **E** = Electricity meter. Consumption in kWh.

## Important rules

1. Convert ALL dates from DD/MM/YYYY to YYYY-MM-DD
2. All monetary amounts are in ZAR — return as plain numbers, no currency symbols
3. For property_size_m2: if shown in hectares (decimal like .2067), multiply by 10000
4. For deposit_amount: remove the trailing minus sign, return as positive number
5. The municipality name may not be explicitly stated — infer from:
   - VAT registration number (4700102181 = Stellenbosch)
   - Postal address on letterhead
   - Phone area code (021 = Western Cape metros)
6. Province: infer from municipality (Stellenbosch = Western Cape)
7. property_type: infer from zoning code. "RES" = house. "Sectional Title" = apartment. If unclear, use null.

## Confidence scoring

Rate each field 0-100:
- **95-100**: Clearly printed, unambiguous, exact match to a labelled field
- **85-94**: Present on bill but needs minor interpretation (e.g., address assembly from multiple lines)
- **70-84**: Requires inference from context (e.g., municipality from VAT number)
- **50-69**: Moderate inference (e.g., property_type from zoning code)
- **Below 50**: Uncertain guess — prefer null over a low-confidence value

Today's date: {today}"""
```

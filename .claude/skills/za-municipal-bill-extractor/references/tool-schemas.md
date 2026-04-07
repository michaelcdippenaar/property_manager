# Municipal Bill Tool Schema

Complete Anthropic tool_use schema for the municipal bill extractor.

## `MUNICIPAL_BILL_TOOL`

```python
MUNICIPAL_BILL_TOOL = {
    "name": "submit_municipal_bill_data",
    "description": (
        "Submit structured property and billing data extracted from a South African "
        "municipal bill / rates account. Every field must come directly from the document. "
        "Use null for fields not found. Provide a confidence_score (0-100) for each "
        "extracted field."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # ── Property identification ──────────────────────────────
            "property_name": {
                "type": ["string", "null"],
                "description": "Short property label — typically the street address or estate name as shown on the bill. E.g. '4 Otterkuil Street, Karindal' or '18 Irene Park, La Colline'."
            },
            "address": {
                "type": ["string", "null"],
                "description": "Full street address including street number, street name, and suburb/area. E.g. '4 Otterkuil Street, Karindal, Stellenbosch, 7600'."
            },
            "city": {
                "type": ["string", "null"],
                "description": "City or town name. E.g. 'Stellenbosch', 'Cape Town', 'Johannesburg'."
            },
            "province": {
                "type": ["string", "null"],
                "description": "Province. One of: Western Cape, Eastern Cape, Northern Cape, Free State, KwaZulu-Natal, North West, Gauteng, Mpumalanga, Limpopo."
            },
            "postal_code": {
                "type": ["string", "null"],
                "description": "4-digit South African postal code. E.g. '7600'."
            },
            "erf_number": {
                "type": ["string", "null"],
                "description": "Erf/stand/plot number as shown. Stellenbosch format: 'MDRIF 4087 00001' or 'LACOL 2689 00001'. Other municipalities may use 'Erf 1234' or 'Stand 567'. Return exactly as printed."
            },
            "municipal_account_number": {
                "type": ["string", "null"],
                "description": "The municipal account number. E.g. '10831902', '10884405'. Usually 7-9 digits."
            },
            "property_type": {
                "type": ["string", "null"],
                "enum": ["apartment", "house", "townhouse", "commercial", null],
                "description": "Infer from zoning/usage code on the bill. 'RES' or 'Residential' = house/townhouse. 'Sectional Title' = apartment. 'BUS' or 'Commercial' = commercial. If unclear, use null."
            },

            # ── Owner information ────────────────────────────────────
            "owner_name": {
                "type": ["string", "null"],
                "description": "Account holder / property owner name as printed. E.g. 'KLIKK (PTY) LTD', 'J SMITH'."
            },
            "owner_id_or_reg": {
                "type": ["string", "null"],
                "description": "Owner's ID number or company registration number if shown on the bill."
            },

            # ── Property details ─────────────────────────────────────
            "zoning": {
                "type": ["string", "null"],
                "description": "Zoning or usage code. E.g. 'RES' (residential), 'BUS' (business), 'IND' (industrial). Return as shown on bill."
            },
            "property_size_m2": {
                "type": ["number", "null"],
                "description": "Property size in m² or hectares (convert to m²). Stellenbosch bills show this in the AREA field, e.g. '.2067' hectares = 2067 m²."
            },
            "valuation": {
                "type": ["number", "null"],
                "description": "Municipal valuation amount in ZAR. E.g. 9640000."
            },

            # ── Billing amounts ──────────────────────────────────────
            "rates_amount": {
                "type": ["number", "null"],
                "description": "Monthly property rates amount in ZAR (excl VAT). Look for 'Rates Monthly' line item."
            },
            "refuse_amount": {
                "type": ["number", "null"],
                "description": "Refuse/waste removal amount in ZAR (incl VAT). Look for 'Refuse Removal' line."
            },
            "sewerage_amount": {
                "type": ["number", "null"],
                "description": "Sewerage levy in ZAR (incl VAT). Look for 'Sewerage Levy' line."
            },
            "water_amount": {
                "type": ["number", "null"],
                "description": "Total water charges in ZAR (basic + consumption, incl VAT)."
            },
            "electricity_amount": {
                "type": ["number", "null"],
                "description": "Total electricity charges in ZAR (basic + consumption, incl VAT)."
            },
            "total_due": {
                "type": ["number", "null"],
                "description": "Total amount now due in ZAR. Look for 'TOTAL NOW DUE' or 'Total monthly'."
            },

            # ── Meter information ────────────────────────────────────
            "water_meter_number": {
                "type": ["string", "null"],
                "description": "Water meter number. Look for 'W' service type row. E.g. '0000049646'."
            },
            "water_consumption": {
                "type": ["number", "null"],
                "description": "Water consumption in kilolitres for the billing period."
            },
            "electricity_meter_number": {
                "type": ["string", "null"],
                "description": "Electricity meter number. Look for 'E' service type row. E.g. '0000744895'."
            },
            "electricity_consumption": {
                "type": ["number", "null"],
                "description": "Electricity consumption in kWh for the billing period."
            },

            # ── Dates ────────────────────────────────────────────────
            "billing_date": {
                "type": ["string", "null"],
                "description": "Account/billing date in YYYY-MM-DD format. Look for 'Account Date' / 'Datum'."
            },
            "due_date": {
                "type": ["string", "null"],
                "description": "Payment due date in YYYY-MM-DD format. Look for 'Due Date' / 'Datum Verskuldig'."
            },
            "billing_period": {
                "type": ["string", "null"],
                "description": "Billing period as shown, e.g. '2026/03' or 'March 2026'."
            },

            # ── Municipality ─────────────────────────────────────────
            "municipality": {
                "type": ["string", "null"],
                "description": "Municipality name. Infer from letterhead, address, or VAT number. E.g. 'Stellenbosch Municipality', 'City of Cape Town'."
            },

            # ── Deposit / guarantee ──────────────────────────────────
            "deposit_amount": {
                "type": ["number", "null"],
                "description": "Deposit or guarantee amount if shown. Stellenbosch bills show this as a negative (credit) amount."
            },

            # ── Confidence scores ────────────────────────────────────
            "confidence_scores": {
                "type": "object",
                "description": "Map of field_name to confidence score (0-100). 90-100 = clearly printed. 70-89 = present but needs interpretation. 40-69 = inferred from context. 0-39 = uncertain guess.",
                "additionalProperties": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                }
            }
        },
        "required": [
            "property_name",
            "address",
            "municipal_account_number",
            "owner_name",
            "total_due",
            "municipality",
            "confidence_scores"
        ]
    }
}
```

## Usage Pattern

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": content}],
    tools=[MUNICIPAL_BILL_TOOL],
    tool_choice={"type": "tool", "name": "submit_municipal_bill_data"}
)

# Extract the structured result — already a dict, no JSON parsing
for block in response.content:
    if block.type == "tool_use":
        extracted = block.input  # Guaranteed to match schema
        break
```

# Field Mapping & HTML Rules

---

## Allowed HTML Tags

Only these tags — TipTap editor renders only these:
- `<h1>`, `<h2>`, `<h3>` — headings
- `<p>` — paragraphs
- `<ul>`, `<ol>`, `<li>` — lists
- `<strong>`, `<em>`, `<u>` — inline formatting
- `<hr>` — horizontal divider
- `<span data-merge-field="field_name">{{ field_name }}</span>` — merge fields

**Do NOT use:** `<div>`, `<table>`, `<span>` (except merge fields), `<br>`, `<html>`, `<body>`, `<style>`

---

## Merge Field Syntax

```html
<span data-merge-field="tenant_name">{{ tenant_name }}</span>
```

Plain `{{ tenant_name }}` text will NOT render as a chip in the editor.

---

## SA Lease Field Categories

| Category | Fields |
|----------|--------|
| **Landlord** | `landlord_name`, `landlord_registration_no`, `landlord_vat_no`, `landlord_representative`, `landlord_title`, `landlord_contact`, `landlord_email`, `landlord_physical_address` |
| **Tenant 1** | `tenant1_name`, `tenant1_id_number`, `tenant1_contact`, `tenant1_email` |
| **Tenant 2** | `tenant2_name`, `tenant2_id_number`, `tenant2_contact`, `tenant2_email` |
| **Property** | `property_address`, `property_suburb`, `property_city`, `property_area_code`, `property_unit_number`, `property_description`, `property_max_occupants` |
| **Lease terms** | `lease_start_date`, `lease_end_date`, `lease_period`, `early_termination_penalty` |
| **Financial** | `monthly_rent`, `monthly_rent_words`, `deposit_amount`, `deposit_amount_words`, `escalation_percentage` |
| **Banking** | `bank_name`, `account_holder`, `account_no`, `branch_name`, `branch_code`, `account_type`, `payment_reference` |
| **Utilities** | `included_utilities`, `tenant_utilities` |
| **Signatures** | `landlord_signature_date`, `tenant1_signature_date`, `tenant2_signature_date`, `witness1_name`, `witness2_name` |

---

## Variable Identification Tips

- Blank lines or underscores after labels: `"Name: ___________"` → merge field
- Square bracket placeholders: `[Tenant Name]` → merge field
- Angle bracket placeholders: `<insert date>` → merge field
- Real data that should be templated (names, addresses, amounts, dates)
- Table cells with labels paired with values or empty cells
- Bank details are **always** variables
- Legal boilerplate text is **NOT** a variable — keep as static text

---

## Standard SA Lease Section Structure

```html
<h1>RESIDENTIAL LEASE AGREEMENT</h1>
<p>(In terms of the Rental Housing Act 50 of 1999, as amended)</p>
<hr>

<h2>1. PARTIES</h2>
<h3>1.1 Landlord</h3>
<h3>1.2 Tenant(s)</h3>

<h2>2. PREMISES</h2>
<h2>3. LEASE PERIOD</h2>
<h2>4. RENTAL AND DEPOSIT</h2>
<h2>5. UTILITIES</h2>
<h2>6. OCCUPANCY</h2>
<h2>7. MAINTENANCE AND REPAIRS</h2>
<h2>8. INSPECTIONS</h2>
<h2>9. NOTICE AND TERMINATION</h2>
<h2>10. CONSUMER PROTECTION ACT</h2>
<h2>11. PROTECTION OF PERSONAL INFORMATION (POPIA)</h2>
<h2>12. DISPUTE RESOLUTION</h2>
<h2>13. SIGNATURES</h2>
```

---

## Fields Schema Format

```json
[
  {"ref": "landlord_name", "label": "Landlord Name", "type": "text"},
  {"ref": "tenant1_name", "label": "Tenant 1 Name", "type": "text"},
  {"ref": "monthly_rent", "label": "Monthly Rent", "type": "text"},
  {"ref": "lease_start_date", "label": "Lease Start Date", "type": "text"}
]
```

Every `data-merge-field` value in the HTML must have a matching entry in the fields array, and vice versa.

---
discovered_by: ux-onboarding
discovered_during: UX-002
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: UX
---

## What I found
The tenant Lease tab shows monthly rent amount and due day but gives the tenant no information on HOW to pay — no banking details, no EFT reference, no payment method explanation. The `Lease` model stores a `payment_reference` field and the `Property`/`Landlord` models store `BankAccount` records, but none of this is surfaced in the tenant portal.

## Why it matters
A tenant who cannot find where to pay rent will either miss the due date (triggering an arrears flag) or call the agent. This is the single highest-frequency query in any property management business. Every active tenant is affected on a monthly basis.

## Where I saw it
- `tenant/src/views/leases/LeaseView.vue` — Lease Details section shows rent amount and due day; no payment section
- `backend/apps/leases/models.py:72` — `payment_reference` field exists on `Lease`
- `backend/apps/properties/models.py:222-229` — `BankAccount` with `bank_name`, `branch_code`, `account_number` exists
- `backend/apps/leases/schema.py:109` — `payment_reference` is in the serializer but not rendered

## Suggested acceptance criteria (rough)
- [ ] Lease tab surfaces a "How to pay" section with: bank name, account number, branch code, account holder, and unique payment reference
- [ ] Payment reference is displayed in a copyable monospace field
- [ ] Tenant serializer/endpoint exposes payment details scoped to their lease only
- [ ] Section also states the due date (already present) and the consequence of late payment per RHA

## Why I didn't fix it in the current task
Requires backend serializer changes and a new UI section. Out of scope for the audit task.

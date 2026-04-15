# Platform Modules & SA Context

---

## Module Registry

| Module | Domain |
|--------|--------|
| `accounts` | Auth, JWT, OTP, OAuth, roles, POPIA |
| `properties` | Properties, units, landlords, banking, ownership |
| `leases` | Lease agreements, TipTap templates, AI builder, clauses, RHA |
| `maintenance` | Requests, suppliers, dispatch, quotes, AI agent, matching algo |
| `esigning` | Gotenberg PDF, audit trail, public links (native signing only) |
| `ai` | Claude integration, lease parsing, tenant intelligence, skills registry |
| `tenant_portal` | Tenant AI chat, maintenance ticket creation, heuristics, throttles |
| `notifications` | Firebase push, email — **priority coverage gap** |

---

## SA Context for Tests

- **POPIA** — personal data must not leak across tenant/owner/agent boundaries; test this explicitly
- **RHA** — Rental Housing Act; lease tests must cover mandatory clause validation and 20-business-day notice
- **ZAR** — all monetary amounts in South African Rand
- **Email domains** — use `@tremly.co.za` or `@test.com` in test accounts
- **SA ID numbers** — use valid 13-digit SA ID format in identity tests

---

## Issue File Template

Create at: `backend/apps/test_hub/issues/<module>/YYYY-MM-DD_<slug>.md`

```markdown
# Issue: <title>
**Module:** <module>
**Status:** RED | FIXED
**Discovered:** <date> (manual testing)
**Test file:** apps/test_hub/<module>/<tier>/test_<file>.py::<Class>::<method>

## Description
## Reproduction Steps
## Root Cause
## Fix Applied
## Test Coverage
- New test: `<path>`
- Duplicate check: confirmed NOT covered — checked: <list>
## Status History
```

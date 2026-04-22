# RHA Compliance Gate — Klikk Rentals v1

## Overview

Every lease that leaves Klikk must satisfy the Rental Housing Act (RHA) Act 50 of 1999 minimum requirements under s5. From v1 onward, **blocking RHA compliance flags prevent a lease from being sent for signing**. Advisory flags generate warnings but do not halt the workflow.

---

## How it works

### 1. Flag generation

When an operator clicks "Send for Signing", the backend runs `rha_check.run_rha_checks(lease)` and stores the results on `Lease.rha_flags`. Flags have the following structure:

```json
{
  "code":     "DEPOSIT_EXCEEDS_2X_RENT",
  "section":  "RHA s5(3)(g)",
  "severity": "blocking",
  "message":  "Deposit (R15 000.00) exceeds two months' rent (R10 000.00).",
  "field":    "deposit"
}
```

| `severity`  | Behaviour |
|-------------|-----------|
| `blocking`  | Prevents `send_for_signing`. Operator sees a red banner with a "Resolve" CTA pointing to the affected field. |
| `advisory`  | Yellow warning banner. Does not prevent signing. |

### 2. Blocking checks (must be cleared)

| Code | RHA Section | Issue |
|------|-------------|-------|
| `MISSING_PRIMARY_TENANT` | s5(3)(a) | No primary tenant linked |
| `MISSING_PREMISES` | s5(3)(b) | No unit linked |
| `MISSING_RENT` | s5(3)(c) | Monthly rent is zero or unset |
| `MISSING_START_DATE` | s5(3)(d) | Start date missing |
| `MISSING_END_DATE` | s5(3)(d) | End date missing |
| `END_BEFORE_START` | s5(3)(d) | End date is on or before start date |
| `MISSING_NOTICE_PERIOD` | s5(3)(e) | Notice period not set |
| `MISSING_DEPOSIT_FIELD` | s5(3)(f) | Deposit field is null |
| `DEPOSIT_EXCEEDS_2X_RENT` | s5(3)(g) | Deposit > 2 × monthly rent |
| `NOTICE_PERIOD_TOO_SHORT` | s5(3)(c) | Notice period < 20 days |

### 3. Advisory checks (warnings only)

| Code | RHA Section | Issue |
|------|-------------|-------|
| `PRO_RATA_FIRST_MONTH` | s5(3) | Lease doesn't start on the 1st — first month may need to be pro-rated |
| `DEPOSIT_INTEREST_BEARING_REMINDER` | s5(3)(h) | Reminder that deposit must be held in an interest-bearing account |
| `MISSING_INSPECTION_IN_EVENT` | s5(4) | No move-in inspection event scheduled |
| `MISSING_INSPECTION_OUT_EVENT` | s5(5) | No move-out inspection event scheduled |

---

## Operator override

When a blocking flag cannot be resolved immediately (e.g. the landlord has a verbal arrangement that doesn't fit the standard data model), an authorised operator can record an override with a reason. The override is **audited** — it stores:

- User ID and email of the overriding user
- The reason provided
- Timestamp (`overridden_at`)
- Snapshot of the blocking flags at the time of override

### Who can override

| Role | Can override |
|------|--------------|
| `admin` | Yes |
| `agency_admin` | Yes |
| Django `is_staff = True` | Yes |
| All other roles | No (`403 Forbidden`) |

### API

```http
POST /api/v1/leases/{id}/rha-override/
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Deposit arrangement verbally confirmed with landlord MC Dippenaar on 2026-04-22"
}
```

Response `200 OK`:
```json
{
  "detail": "RHA compliance override recorded.",
  "rha_override": {
    "user_id": 1,
    "user_email": "admin@klikk.co.za",
    "reason": "...",
    "overridden_at": "2026-04-22T09:30:00Z",
    "flags_at_override": [...]
  }
}
```

### To refresh flags without overriding

```http
GET /api/v1/leases/{id}/rha-check/
```

Returns updated `rha_flags`, `rha_override`, and `blocking_count`.

---

## Admin SPA

The `ESigningPanel` component (`admin/src/views/leases/ESigningPanel.vue`) automatically:

1. Fetches RHA flags on mount via `GET /api/v1/leases/{id}/rha-check/`
2. Shows a **red banner** listing blocking flags with the relevant RHA section and field name
3. The "Send for Signing" button is **disabled** while blocking flags are unresolved (and no override is recorded)
4. Shows a **yellow banner** for advisory reminders (non-blocking)
5. Provides an inline override form (visible to all but only succeeds for authorised roles)
6. Shows a confirmation banner when an override has been recorded (with user + reason)

---

## Legal reference

- **RHA s5(3)**: Minimum content requirements for written lease agreements
- **RHA s5(4)**: Joint inspection of premises at commencement
- **RHA s5(5)**: Joint inspection of premises at termination
- **CPA s14**: Maximum lease term / cooling-off (advisory only — handled in the AI builder)

Full legal text: `.claude/skills/rental-agreement/references/sa-rental-law.md`

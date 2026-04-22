---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-001
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
The `/welcome` redirect in `tenant/src/router/index.ts` uses `sessionStorage` (per-tab, cleared on tab close). Opening a new tab after dismissing the welcome screen redirects the tenant again. The implementer flagged this in handoff notes.

## Why it matters
Tenants who are fully onboarded will keep seeing the welcome screen every time they open a new tab, which is disruptive UX once onboarding is complete and degrades trust in the product.

## Where I saw it
- `tenant/src/router/index.ts:129–141` — guard uses `klikk_welcome_seen` / `klikk_welcome_checked` in `sessionStorage`

## Suggested acceptance criteria (rough)
- [ ] Welcome redirect is suppressed permanently once the tenant has dismissed it (durable across tabs/sessions)
- [ ] Preferred implementation: a `seen_welcome_at` DateTimeField on the User or Tenant model, set via a lightweight API call when `goHome()` is invoked
- [ ] Fallback acceptable: `localStorage` keyed by user ID (no backend change, but still cleared on logout — verify acceptability with PM)

## Why I didn't fix it in the current task
Implementer correctly identified it as out-of-scope for this task. Fixing it requires either a backend model change (User/Tenant field) or a deliberate decision to use localStorage. PM needs to decide.

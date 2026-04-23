---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-045
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
`admin/src/views/leases/ESigningPanel.vue:839` contains a hard-coded default signer with `email: 'mc@tremly.com'` and phone `'0821234567'`, labelled "Pre-populated test defaults (remove before production)". Not a credential leak, but ships a real internal email address as the default recipient when the lease has no tenants.

## Why it matters
- Real staff email shipped in production JS bundle.
- Risk of accidentally triggering real e-sign requests to MC during agent testing.
- Comment explicitly says "remove before production".

## Where I saw it
- `admin/src/views/leases/ESigningPanel.vue:836-840`

## Suggested acceptance criteria (rough)
- [ ] Remove the pre-populated test signer block, or guard behind `import.meta.env.DEV`.
- [ ] If dev-only stub is still wanted, source from env var (same pattern as RNT-SEC-045).
- [ ] `grep -r 'mc@tremly.com' admin/src` returns zero matches.

## Why I didn't fix it in the current task
Out of scope for RNT-SEC-045 (agent-app login pre-fill). Different file, different concern (signer default vs login pre-fill), no password exposure.

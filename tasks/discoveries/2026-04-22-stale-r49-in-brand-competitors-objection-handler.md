---
discovered_by: rentals-reviewer
discovered_during: GTM-011
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: GTM
---

## What I found
`content/brand/competitors.md:57` still contains `R49/unit` in the "Too expensive" objection response — the same stale per-unit pricing that GTM-011 purged from the sales/ files.

## Why it matters
Any agent or marketer referencing the brand competitive file will see the old pricing, contradicting demo-flow.md and persona objection handlers that were updated in GTM-011. Creates inconsistent messaging at the point of sale.

## Where I saw it
- `content/brand/competitors.md:57` — objection handler table row: `"Too expensive" | R49/unit saves 5+ admin hours/month. Free for up to 5 units.`

## Suggested acceptance criteria (rough)
- [ ] `content/brand/competitors.md:57`: replace `R49/unit saves 5+ admin hours/month` with flat-rate reframe consistent with `content/product/pricing.yaml` (Pro R2,500/month, Enterprise R4,000/month)
- [ ] `grep -r "R49\|R39/unit" content/` returns zero matches

## Why I didn't fix it in the current task
Out of scope — GTM-011 was scoped to content/sales/ only. competitors.md is a brand/ file; the PM should decide the updated objection language.

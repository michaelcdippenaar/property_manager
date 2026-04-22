---
discovered_by: gtm-marketer
discovered_during: GTM-009
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: GTM
---

## What I found

Several sales content files reference a legacy R49/unit/month pricing model that no longer exists in `content/product/pricing.yaml`. Current pricing is flat-rate: Free (5 properties), Pro (R2,500/month), Enterprise (R4,000/month base). The R49/unit model is gone entirely.

## Why it matters

Sales reps and demo scripts quoting R49/unit are giving prospects incorrect pricing. If a prospect researches further or hears a conflicting number, it damages trust and undermines the demo close. The stale MRR projections in icp.md also misrepresent Klikk's revenue model to anyone using the ICP for business planning.

## Where I saw it

- `content/sales/demo-flow.md:57` — "The Professional tier is R49/unit — for 20 properties that's R980/month"
- `content/sales/icp.md:116` — "Likely paying users (6–10 units, R49/unit) | ~20%"
- `content/sales/icp.md:118` — "MRR potential (10% conversion, avg 7 units @ R49) | ~R103 000–R172 000/month"
- `content/sales/personas/persona-01-boutique-pm-principal.md:64` — "R49/unit sounds expensive | Reframe: 45 units = R2 205/month"

## Suggested acceptance criteria (rough)

- [ ] Update `demo-flow.md` pricing section to reflect current flat-rate tiers (Free / Pro R2,500 / Enterprise R4,000)
- [ ] Recalculate or remove the stale MRR projection row in `icp.md` segment size table
- [ ] Update `icp.md` paying-users row to reference Pro tier eligibility (6+ properties), not R49/unit
- [ ] Update persona-01 objection handler to reflect current Pro pricing (R2,500/month flat, not per-unit)
- [ ] Run `grep -r "R49" content/` to catch any remaining occurrences

## Why I didn't fix it in the current task

GTM-009 is scoped to the specific "5 units vs 5 properties" correction in `voice.md` and related free-tier references. The R49/unit pricing issue affects pricing narrative and sales calculations — it warrants its own task and PM sign-off on the correct replacement talking points.

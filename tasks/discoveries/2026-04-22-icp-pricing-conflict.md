---
discovered_by: gtm-marketer
discovered_during: GTM-007
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: GTM
---

## What I found

`content/sales/icp.md` and `content/sales/objections.md` both reference a "R49/unit/month" per-unit pricing model (e.g. "10 properties = R490/month") that does not exist in `content/product/pricing.yaml`. The current pricing model is per-organisation (Pro at R2,500/month for up to 100 units, Enterprise at R4,000/month). There is no per-unit pricing tier in pricing.yaml.

## Why it matters

Any agent using the ICP or objections files as a script will quote incorrect pricing to prospects. The demo-flow.md also closes with a per-unit pricing pitch ("R49/unit"). A prospect told "R490/month for 10 properties" and then invoiced R2,500/month will have grounds to walk away and will not trust Klikk.

## Where I saw it

- `content/sales/icp.md` — "Budget: R49/unit/month" in two ICP segments
- `content/sales/objections.md` — "At R49/unit, managing 10 properties costs R490/month"
- `content/sales/demo-flow.md` — "The Professional tier is R49/unit — for 20 properties that's R980/month"
- `content/product/pricing.yaml` — No per-unit tier exists; Pro = R2,500/month flat for up to 100 units

## Suggested acceptance criteria (rough)

- [ ] Update `content/sales/icp.md` to reflect current pricing.yaml tiers (Pro R2,500/month, Enterprise R4,000/month)
- [ ] Update `content/sales/objections.md` pricing objection response to use current pricing
- [ ] Update `content/sales/demo-flow.md` pricing close to use current pricing
- [ ] Add a pricing reference note at the top of each sales file pointing to pricing.yaml as the authoritative source
- [ ] Confirm with PM whether a per-unit pricing model was deprecated or was never shipped — update pricing.yaml if the per-unit model was intentional

## Why I didn't fix it in the current task

The ICP and objections files are in scope for a separate task (GTM-002 or equivalent). Rewriting them under GTM-007 would inflate scope and create an unreviewed change to foundational sales materials. GTM-007 deliverables (one-pager, deck, intro email) use pricing.yaml directly, not the conflicting sales files.

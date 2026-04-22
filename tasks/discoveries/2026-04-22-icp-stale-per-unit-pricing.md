---
discovered_by: rentals-reviewer
discovered_during: GTM-005
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: GTM
---

## What I found

`content/sales/icp.md` references a per-unit pricing model ("R49/unit") in six places (lines 33, 56, 66, 116, 118, 162) and an "Agency tier" at "R39/unit" (line 162). The current pricing model in `content/product/pricing.yaml` is flat per-organisation (Pro R2,500/month, Enterprise R4,000/month base) — no per-unit fee.

## Why it matters

Sales assets and ICP docs are used in demos and outreach. If an agent quotes R49/unit from icp.md, a 20-unit prospect hears R980/month instead of R2,500/month — wrong in both directions depending on portfolio size. The inconsistency can undermine demo credibility and create pricing confusion for any agent or AI using these docs.

## Where I saw it

- `content/sales/icp.md:56` — "Wins on: price (R49/unit vs R150+)"
- `content/sales/icp.md:66` — "MRR at R49/unit (SAM capture rate 10%)"
- `content/sales/icp.md:116` — "Likely paying users (6–10 units, R49/unit)"
- `content/sales/icp.md:118` — "MRR potential (10% conversion, avg 7 units @ R49)"
- `content/sales/icp.md:162` — "ZAR pricing at Agency tier (R39/unit)"
- `content/sales/demo-flow.md:57` — "The Professional tier is R49/unit — for 20 properties that's R980/month"
- `content/sales/personas/persona-01-boutique-pm-principal.md:64` — "R49/unit sounds expensive | Reframe: 45 units = R2 205/month"
- `content/product/pricing.yaml` — Pro is R2,500/month flat (no per-unit fee); no Agency tier exists

## Suggested acceptance criteria (rough)

- [ ] All R49/unit and R39/unit references in icp.md replaced with correct flat pricing (R2,500/month Pro, R4,000/month Enterprise base)
- [ ] SAM MRR estimates in icp.md recalculated based on flat pricing model or noted as directional estimates pending pricing finalisation
- [ ] demo-flow.md and persona-01 objections updated to use correct pricing language
- [ ] "Agency tier" references removed — no such tier exists in pricing.yaml

## Why I didn't fix it in the current task

Out of scope for GTM-005, which only touches `content/marketing/launch-plan.md`. The icp.md conflict predates this task and requires a PM decision on whether the per-unit model was intentionally abandoned in favour of flat pricing.

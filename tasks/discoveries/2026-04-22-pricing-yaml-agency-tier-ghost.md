---
discovered_by: rentals-reviewer
discovered_during: GTM-002
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: GTM
---

## What I found

`content/product/pricing.yaml` is internally inconsistent: the file header (line 4) and all `available_on` arrays reference an "Agency" tier, but no `agency:` key exists under `tiers:`. The tier at R4,000/month is defined as `enterprise` (name: "Enterprise"). This ghost "Agency" label has already propagated into `content/brand/positioning.md` and `content/brand/competitive-matrix.md` as "R39/unit (Agency tier)" pricing — which has no basis in pricing.yaml at all.

## Why it matters

Any downstream content that reads the header comment or `available_on: [pro, agency, enterprise]` will infer a mid-tier "Agency" product that does not exist. Copy writers, sales scripts, and positioning docs (already demonstrated in GTM-002) will invent per-unit "Agency" pricing to fill the gap. The prior discovery `2026-04-22-icp-pricing-conflict.md` documents the same per-unit fiction in icp.md, objections.md, and demo-flow.md — this is the root cause.

## Where I saw it

- `content/product/pricing.yaml:4` — header comment says "Agency R4,000"
- `content/product/pricing.yaml:200,218,223,239,288,313` — `available_on` arrays include `agency` as if it is a real tier key
- `content/product/pricing.yaml` tiers section — only `free`, `pro`, `enterprise`, `custom` are defined; no `agency` key
- `content/brand/positioning.md:95` — "R39/unit (Agency tier)"
- `content/brand/competitive-matrix.md:40` — "R39 (Agency)" in price-per-unit axis

## Suggested acceptance criteria (rough)

- [ ] Decide (PM): is "Agency" a planned tier distinct from Enterprise, or is Enterprise the correct name for the R4,000 tier?
- [ ] If "Agency" is deprecated / never existed: rename `enterprise` to `agency` in pricing.yaml tiers, OR remove all "Agency" references from comments and `available_on` arrays — whichever reflects commercial intent
- [ ] If "Agency" is a real planned tier: add it as a first-class `agency:` key in pricing.yaml with its own pricing definition
- [ ] Update all `available_on` arrays to reference only tier keys that exist
- [ ] After pricing.yaml is resolved, re-trigger GTM-002 fix so positioning.md and competitive-matrix.md can cite correct tier names and flat-rate pricing

## Why I didn't fix it in the current task

Resolving this requires a commercial decision (does an "Agency" tier exist?). Fixing it unilaterally inside GTM-002 would either invent a tier or rename an existing one — both are above reviewer scope.

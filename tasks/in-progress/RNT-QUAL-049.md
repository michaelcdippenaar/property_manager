---
id: RNT-QUAL-049
stream: rentals
title: "Pricing v1.1 review: evaluate tier rename and per-unit vs flat-rate model post-launch"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.1"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214246263064093"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
After v1.0 launch, revisit the pricing model using real customer feedback and usage data — evaluate the enterprise→agency tier rename, per-unit vs flat-rate positioning, and any new tier options informed by first-client onboarding.

## Context
DEC-016 (answered 2026-04-24) froze `content/product/pricing.yaml` as-is for v1.0 launch. The GTM-010 pricing research report (`content/sales/pricing-research-2026.md`) recommended renaming `enterprise` → `agency` and evaluated per-unit pricing. This v1.1 task is the formal follow-on for that review.

## Acceptance criteria
- [ ] Review `content/sales/pricing-research-2026.md` in light of first-client onboarding data
- [ ] MC signs off on any tier rename before it is applied to `content/product/pricing.yaml`
- [ ] Any approved changes to pricing.yaml propagated to all sales/marketing content files
- [ ] Any code changes (if tier keys change) landed with a migration and feature-flag if needed
- [ ] Updated pricing reflected in website copy

## Files likely touched
- `content/product/pricing.yaml`
- `content/sales/pricing-research-2026.md`
- `content/sales/icp.md`
- `content/sales/demo-flow.md`
- `content/brand/positioning.md`

## Test plan
**Manual:**
- `grep -r "enterprise\|agency" content/` confirms consistent naming across all files after any rename
- MC approves final pricing.yaml diff

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Created as post-launch v1.1 follow-up to DEC-016. Do not start until first-client dry-run data is available.

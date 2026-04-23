---
discovered_by: ux-onboarding
discovered_during: UX-001
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: UX
---

## What I found

The rental lifecycle step "Onboard" (lifecycle.yaml step 11) maps to the `tenant_onboarding` feature which is marked `status: BUILT` with `shipped_date: 2026-03-01`, but `key_files: []`. No frontend UI exists for tenant move-in prep in either the admin web app or the agent mobile app. The incoming inspection feature is PLANNED. There is no move-in checklist, keys handover record, or utilities setup screen anywhere in the product.

## Why it matters

The first rental cycle ends with a signed lease but no UI to support the actual move-in. Agents completing their first tenancy have no in-app workflow for: keys handover, incoming inspection, tenant app invite, utility notification, or welcome pack. The tenant_onboarding feature being marked BUILT with no key files is also a data integrity issue in features.yaml.

## Where I saw it

- `content/product/features.yaml`: `tenant_onboarding.status: BUILT`, `tenant_onboarding.key_files: []`
- `content/product/features.yaml`: `incoming_inspection.status: PLANNED`
- No Vue component found in `admin/src/` or `agent-app/src/` matching "onboard", "move-in", or "inspection" (incoming)

## Suggested acceptance criteria (rough)

- [ ] `tenant_onboarding` in features.yaml is corrected to reflect actual built state
- [ ] A minimum viable move-in checklist is added to the lease detail view (keys, utilities, welcome pack — checkbox per item)
- [ ] The checklist state is persisted per lease (backend endpoint or lease field)
- [ ] Incoming inspection design is scoped and added to roadmap

## Why I didn't fix it in the current task

Requires product decision on scope of v1 move-in prep. Backend work needed. Out of scope for a UX audit.

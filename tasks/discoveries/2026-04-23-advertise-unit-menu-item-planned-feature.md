---
discovered_by: ux-onboarding
discovered_during: UX-001
discovered_at: 2026-04-23
priority_hint: P0
suggested_prefix: UX
---

## What I found

The property detail Actions dropdown includes "Advertise unit" as a menu item, but the underlying feature (`property_advertising`) has `status: PLANNED` in `features.yaml`. The menu item is present in production UI for an unbuilt feature.

## Why it matters

Every agent who clicks "Advertise unit" after signing their first mandate will hit a dead end — either a 404, an empty state with no explanation, or a silent failure. This occurs at the most critical moment in the first rental cycle (after mandate is active, agent tries to list the vacancy). It actively destroys trust on day one.

## Where I saw it

- `admin/src/views/properties/PropertyDetailView.vue` line ~98: `<button class="menu-item" @click="handleAdvertise">Advertise unit</button>`
- `content/product/features.yaml`: `property_advertising.status: PLANNED`

## Suggested acceptance criteria (rough)

- [ ] "Advertise unit" menu item is hidden or disabled with a "Coming soon" tooltip when `property_advertising` is PLANNED
- [ ] No PLANNED features appear as active nav items or action buttons in production builds
- [ ] A process is agreed for gating UI items on feature status

## Why I didn't fix it in the current task

Out of scope for a UX audit. Requires a decision on how to handle feature-gated UI items (hide vs disable vs "coming soon" badge).

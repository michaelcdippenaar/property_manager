---
id: RNT-QUAL-069
stream: rentals-quality
title: "Wire or remove dead click affordance in AgencyShellView dashboard event feed"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214274243223437"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Eliminate dead clicks on the agent dashboard event feed: either route each event type to its existing detail view or remove the click affordance until routing is implemented.

## Acceptance criteria

- [x] `admin/src/views/dashboard/AgencyShellView.vue:48-52` (`handleEventAction`): the `// TODO: route to the relevant detail view` stub is resolved.
- [x] Option A (preferred): each known event type (`lease`, `maintenance`, `inspection`, `signing`, `viewing`) is routed to its existing detail view using Vue Router.
- [ ] Option B (fallback): the click affordance (e.g. cursor pointer, hover highlight) is removed from event row chips and `handleEventAction` is either a no-op with a comment or deleted until routing exists.
- [x] No `console.log` remains in `handleEventAction` (covered by RNT-QUAL-065 but confirm here too).
- [x] No unhandled navigation errors — unknown event types are handled gracefully.

## Files likely touched

- `admin/src/views/dashboard/AgencyShellView.vue` (lines 48-52)
- Possibly event row child component (if click affordance lives there)

## Test plan

**Manual:**
- Click each event type chip in the agent dashboard; confirm navigation or disabled state, no console errors.

**Automated:**
- `cd admin && npm run test:unit` (if unit tests cover the dashboard shell)

## Handoff notes

Promoted from discovery `2026-04-24-agency-shell-event-action-todo.md` (2026-04-24). P2 — dead clicks on the highest-traffic surface at v1 launch are a credibility hit for agents.

**2026-04-24 -- implementer**
Chose Option A. Wired handleEventAction in AgencyShellView.vue with a switch on eventClass. maintenance/gate->maintenance-detail (deep-link via propertyId) or maintenance-issues fallback. lease/renewal/signing->leases. rent/refund->payments. inspection/compliance/viewing->properties. Unknown->silent no-op. Added useRouter + EventItem imports.

**2026-04-24 -- reviewer**
Review passed. Checked: useRouter + router.push wired correctly; switch covers all AC event classes plus gate/renewal/refund/compliance extras; maintenance-detail, maintenance-issues, leases, payments, and properties all exist in router/index.ts; no console.log present; default no-op handles unknown classes gracefully. One pre-existing vue-tsc error (focus-trap-keyboard.browser.test.ts) is unrelated.

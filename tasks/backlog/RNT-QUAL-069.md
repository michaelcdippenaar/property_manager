---
id: RNT-QUAL-069
stream: rentals-quality
title: "Wire or remove dead click affordance in AgencyShellView dashboard event feed"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214274243223437"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Eliminate dead clicks on the agent dashboard event feed: either route each event type to its existing detail view or remove the click affordance until routing is implemented.

## Acceptance criteria

- [ ] `admin/src/views/dashboard/AgencyShellView.vue:48-52` (`handleEventAction`): the `// TODO: route to the relevant detail view` stub is resolved.
- [ ] Option A (preferred): each known event type (`lease`, `maintenance`, `inspection`, `signing`, `viewing`) is routed to its existing detail view using Vue Router.
- [ ] Option B (fallback): the click affordance (e.g. cursor pointer, hover highlight) is removed from event row chips and `handleEventAction` is either a no-op with a comment or deleted until routing exists.
- [ ] No `console.log` remains in `handleEventAction` (covered by RNT-QUAL-065 but confirm here too).
- [ ] No unhandled navigation errors — unknown event types are handled gracefully.

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

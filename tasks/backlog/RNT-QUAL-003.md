---
id: RNT-QUAL-003
stream: rentals
title: "Global loading / empty / error states across admin SPA"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177379596082"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Replace every ad-hoc spinner, blank table, and red toast with three consistent, branded states: `<LoadingState>`, `<EmptyState>`, `<ErrorState>` — used everywhere a list or detail page fetches data.

## Acceptance criteria
- [ ] `admin/src/components/states/LoadingState.vue` — skeleton, branded, accessible (aria-busy)
- [ ] `admin/src/components/states/EmptyState.vue` — icon + copy + primary CTA slot + secondary link slot
- [ ] `admin/src/components/states/ErrorState.vue` — copy + retry button + "contact support" link
- [ ] Audit every list view and detail view; replace ad-hoc states
- [ ] Storybook or `/components` preview page demonstrates each state
- [ ] Empty-state copy: warm, action-oriented, follows `content/brand/voice.md`
- [ ] All tables use skeleton rows while loading, not spinner overlays

## Files likely touched
- `admin/src/components/states/*.vue` (3 new)
- Every `admin/src/views/**/*.vue` list/detail page (batch edit)

## Test plan
**Manual:**
- Offline mode in DevTools → every page shows ErrorState with Retry
- Fresh account with no data → every page shows EmptyState with helpful CTA
- Slow network throttle → LoadingState skeletons, not spinners

## Handoff notes

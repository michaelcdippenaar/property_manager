---
id: RNT-AI-004
stream: rnt-ai
title: "AI window close → owner navigation crashes"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: review
assigned_to: null
depends_on: []
asana_gid: "1214278059913632"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Identify and fix the JS crash / Vue error that occurs when a user closes the AI chat widget and then navigates to the Owners (Landlords) view in the admin SPA.

## Acceptance criteria

- [ ] Bug reproduced locally and exact JS error / Vue warning captured from browser console.
- [ ] Root cause identified (likely candidates: stale event listener, undisposed watcher, Pinia store mutation on unmounted component, router guard reading destroyed state, AI chat overlay portal not cleaned up on close).
- [ ] Fix applied — close handler fully unmounts/cleans up the AI chat widget and disposes all listeners and watchers.
- [ ] Regression test added (e.g. Vitest unit test asserting store is clean post-close, or Playwright smoke: open chat → close → navigate to /owners → assert no console errors).
- [ ] Verify: open AI chat → close → navigate to /owners (or /landlords) → page renders cleanly with zero console errors and zero Vue warnings.

## Files likely touched

- `admin/src/components/ai/` (chat widget, close handler)
- `admin/src/stores/aiGuide.ts` (or equivalent AI store)
- `admin/src/views/owners/` OR `admin/src/views/landlords/`
- `admin/src/router/index.ts` (router guards)

## Test plan

**Manual:**
1. Log in to admin SPA.
2. Open the AI chat widget.
3. Close the AI chat widget.
4. Click "Owners" (or "Landlords") in the sidebar navigation.
5. Observe: page must render cleanly. Open DevTools console — must show zero errors and zero Vue warnings.

**Automated:**
- Vitest: assert that the AI store resets to a clean state after the close action is dispatched.
- Playwright (E2E): open chat → close → navigate to /owners → `expect(page).toHaveNoConsoleErrors()`.

## Handoff notes

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-25 — rentals-pm: Task created from MC repro report. Exact error stack not yet captured; implementer must reproduce first. Note: the Opus agent currently auditing AI chat may already fix this — if so, mark as "already implemented" and move directly to review.

2026-04-25 — rentals-pm: Already implemented by Opus AI-chat audit on 2026-04-25, ready for review. Fixed in commit `f37a3624` — fix(ai-guide): close()→nav crash bulletproofing. Backend 61/61 ai/ tests pass.

---
id: RNT-AI-001
stream: rentals-ai
title: "AI guide highlight affordance missing — highlighted button not visible on screen"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: null
depends_on: []
asana_gid: "1214278001636336"
created: 2026-04-25
updated: 2026-04-25
---

## Goal
When the AI guide says it has highlighted a UI element, a visible CSS ring / glow actually appears on that element in the admin SPA.

## Acceptance criteria
- [ ] Asking the AI guide "Create a new property" causes the Add Property button to display a visible highlight ring/glow (e.g. `outline`, `box-shadow`, or a named CSS class) for at least 3 seconds.
- [ ] The highlight is removed cleanly after the timeout or on user interaction, leaving no residual styles.
- [ ] The highlight mechanism works across all major admin SPA buttons that the AI guide may reference (not just Add Property).
- [ ] No console errors thrown during highlight attach/detach.

## Repro steps
1. Open admin SPA → AI chat widget.
2. Ask "Create a new property".
3. AI responds saying it has highlighted the Add Property button.
4. Observe: no visible highlight ring or glow appears on the button.

## Files likely touched
- `admin/src/components/AiGuide/` (highlight trigger logic)
- `admin/src/composables/useAiGuide.ts` or equivalent composable
- `admin/src/assets/ai-guide.css` or global stylesheet (highlight CSS class)
- Possibly `backend/apps/ai/views.py` if highlight instruction originates from the backend response payload

## Test plan
**Manual:**
- Repro steps above; verify visible highlight ring appears.
- Verify highlight disappears after timeout.
- Test on Firefox and Chrome (ensure `outline` fallback works).

**Automated:**
- Add a Playwright/Vitest assertion that the DOM element matching the highlighted selector has a non-empty `outline` or `box-shadow` computed style after AI guide triggers a highlight action.

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-25 — rentals-pm: Filed from MC's direct repro. Highlight CSS / DOM marker is missing or not being applied when the AI guide instructs a UI element highlight.

2026-04-25 — rentals-pm: Already implemented by Opus AI-chat audit on 2026-04-25, ready for review. Fixed in commit `5157729d` — fix(ai-guide): highlight actually visible.

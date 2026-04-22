---
discovered_by: rentals-reviewer
discovered_during: QA-007
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: QA
---

## What I found
`BaseModal.vue` and `BaseDrawer.vue` do not trap keyboard focus. When a modal or drawer opens, Tab can escape to background content and focus is not programmatically moved into the dialog on open, nor returned to the trigger element on close.

## Why it matters
WCAG 2.1 SC 2.1.2 (No Keyboard Trap) requires that focus be manageable within dialogs. Without a focus trap, keyboard-only and screen reader users can navigate into obscured background content while a modal is open, breaking the modal interaction contract. Affects the agent golden path (property drawer, lease drawer, confirmation modals).

## Where I saw it
- `admin/src/components/BaseModal.vue` — no `useFocusTrap` or `<dialog>` element
- `admin/src/components/BaseDrawer.vue` — same

## Suggested acceptance criteria (rough)
- [ ] On modal/drawer `open`, focus moves to first focusable element inside the dialog
- [ ] Tab cycles within dialog only; Shift+Tab wraps to last element
- [ ] Escape closes dialog and returns focus to the element that triggered it
- [ ] Implement using `focus-trap` npm package composable or replace `<div role="dialog">` with native `<dialog>` element
- [ ] Tester validates with keyboard-only and VoiceOver

## Why I didn't fix it in the current task
Out of scope for QA-007 static audit; implementing a focus trap composable is a separate effort (estimate: S). Noted as P-001 in `docs/qa/accessibility-2026-04.md`.

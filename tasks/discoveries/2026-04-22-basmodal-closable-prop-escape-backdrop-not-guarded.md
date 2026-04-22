---
discovered_by: rentals-reviewer
discovered_during: QA-011
discovered_at: 2026-04-22
priority_hint: P3
suggested_prefix: QA
---

## What I found
`BaseModal.vue` exposes a `closable` prop intended to prevent dismissal, but neither the backdrop click (`@click="$emit('close')"` on line 13) nor the new Escape keydown path in `useFocusTrap` respect this flag. The X button is correctly hidden via `v-if="closable"`, but the modal can still be closed by clicking the backdrop or pressing Escape regardless.

## Why it matters
Any modal opened with `:closable="false"` (e.g., a mid-flow step the user must complete) is silently dismissible, which could let users bypass required steps.

## Where I saw it
- `admin/src/components/BaseModal.vue:13` — backdrop click unconditionally emits `close`
- `admin/src/composables/useFocusTrap.ts` — Escape always emits `close`, not conditioned on a guard

## Suggested acceptance criteria (rough)
- [ ] Backdrop click in BaseModal is gated on `closable` prop (add `v-if` or pass `closable` to emit handler)
- [ ] `useFocusTrap` accepts an optional `onEscape` callback or the caller passes `null` to disable Escape dismissal; BaseModal passes `null` when `closable: false`

## Why I didn't fix it in the current task
Out of scope; the backdrop click issue pre-dates QA-011 and fixing it cleanly requires a design decision on how `closable` should affect Escape vs. backdrop independently.

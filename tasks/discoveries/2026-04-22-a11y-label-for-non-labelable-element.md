---
discovered_by: rentals-reviewer
discovered_during: QA-007
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: QA
---

## What I found

In `admin/src/views/auth/AcceptInviteView.vue` line 48–49, `<label for="invite-email">` references `<p id="invite-email">`. The HTML spec defines labelable elements as `button`, `input`, `meter`, `output`, `progress`, `select`, and `textarea`. A `<p>` is not labelable, so the `for`/`id` association is not a valid programmatic label relationship and will not be honoured by assistive technologies.

## Why it matters

Screen readers will not announce "Email" when focus moves to (or near) the email display paragraph. For a read-only display value this is a low-severity gap, but it is still a WCAG 1.3.1 failure (Info and Relationships).

## Where I saw it

- `admin/src/views/auth/AcceptInviteView.vue` lines 48–49

## Suggested acceptance criteria (rough)

- [ ] Replace `<p id="invite-email">` with a read-only `<input type="email" id="invite-email" :value="invite.email" readonly tabindex="-1">` (or equivalent), so the `<label for>` association is valid per spec.
- [ ] Alternatively, remove the `<label>` and use a visible text label styled consistently, with `aria-describedby` or a visually-hidden `<span>` if a programmatic association is needed.

## Why I didn't fix it in the current task

The round-1 review explicitly asked for `for`/`id` to be added to this pair. The implementer complied. Changing the element type from `<p>` to `<input readonly>` goes beyond the stated fix and is a separate, targeted change. Raising as a discovery so the PM can schedule it.

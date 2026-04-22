---
discovered_by: rentals-implementer
discovered_during: OPS-005
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: OPS
---

## What I found

The compiled MJML output at `backend/apps/notifications/email_templates/compiled/base.html`
has two Django template conditional blocks (`{% if cta_url %}` and `{% if note %}`) that
were hand-inserted post-compilation. If `base.mjml` is ever recompiled with `npx mjml`,
those conditional blocks are overwritten and the CTA button and note rows will always
render regardless of context, producing blank/broken buttons.

## Why it matters

Any developer who edits `base.mjml` (e.g. to adjust branding) will regenerate the compiled
file and silently break the conditional rendering. No error is thrown — emails just always
show an empty pink button.

## Where I saw it

- `backend/apps/notifications/email_templates/base.mjml` — source template
- `backend/apps/notifications/email_templates/compiled/base.html:148–196` — patched rows

## Suggested acceptance criteria (rough)

- [ ] Add `scripts/compile_email_templates.sh` (or `Makefile` target) that runs `npx mjml`
  and then applies the Django `{% if %}` patch as a `sed` or Python script step
- [ ] Add a CI check (pre-commit hook or GitHub Actions step) that fails if `compiled/base.html`
  is out of date relative to `base.mjml` without the conditional blocks present
- [ ] Document the compile step in `backend/apps/notifications/NOTIFICATIONS.md`

## Why I didn't fix it in the current task

Authoring a robust build script + CI check would expand the task scope significantly beyond
the M-effort estimate for OPS-005. The current hand-patch is stable as long as no one
touches `base.mjml`.

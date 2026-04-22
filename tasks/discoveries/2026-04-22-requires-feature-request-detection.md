---
discovered_by: rentals-reviewer
discovered_during: OPS-007
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
The `@requires_feature` decorator in `backend/apps/accounts/decorators.py` uses runtime isinstance checks to locate the DRF Request in the argument list. If the call signature does not match either the plain FBV or the one-arg CBV pattern (e.g. a view decorated with `@action`, a mixin that injects an extra positional arg, or a custom router that passes `format`), the `request` variable is set to `None` and the gate silently passes through.

## Why it matters
Any future view that applies `@requires_feature` but has a non-standard signature will bypass the tier gate entirely, granting the feature regardless of tier. The issue is invisible — no error, no log line. This is a latent privilege-escalation vector as more features are gated.

## Where I saw it
- `backend/apps/accounts/decorators.py:65–67` (the `else: request = None` branch)

## Suggested acceptance criteria (rough)
- [ ] When request cannot be identified, raise `ImproperlyConfigured` in DEBUG mode and return HTTP 500 in production rather than passing through.
- [ ] Add a test that applies the decorator to a view with an unexpected signature and asserts it does not silently pass.
- [ ] Alternatively, refactor the decorator to rely on a known request-resolver (e.g. `request.parser_context` or a fixed kwarg position) rather than isinstance duck-typing.

## Why I didn't fix it in the current task
Fix touches only the decorator but overlaps with a broader hardening sweep of all `@requires_feature` call sites. Keeping it as a standalone task avoids scope creep on OPS-007 and lets the PM decide priority.

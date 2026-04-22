---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-033
discovered_at: 2026-04-22
priority_hint: P3
suggested_prefix: RNT-QUAL
---

## What I found
`seen_welcome_at` is not in `read_only_fields` on `UserSerializer`, so a tenant can set or clear it via `PATCH /auth/me/`. The dedicated `POST /auth/welcome/` endpoint is idempotent-only-sets, but the general PATCH endpoint has no such constraint.

## Why it matters
A tenant can reset their own welcome screen by patching `seen_welcome_at: null`, or set it to an arbitrary past timestamp. Not a security issue (they own the field), but it's an inconsistency — the dedicated endpoint enforces "once only" semantics that the general patch silently bypasses.

## Where I saw it
- `backend/apps/accounts/serializers.py:140` — `read_only_fields` list does not include `seen_welcome_at`
- `backend/apps/accounts/views.py:161` — `MeView.patch` uses the same serializer with no field-level restrictions

## Suggested acceptance criteria (rough)
- [ ] Add `seen_welcome_at` to `read_only_fields` in `UserSerializer` so it can only be written via the dedicated `POST /auth/welcome/` endpoint
- [ ] Confirm existing tests still pass after the change

## Why I didn't fix it in the current task
Out of scope for RNT-QUAL-033. The implementer's notes explicitly described it as writable by design; PM should decide whether to lock it down.

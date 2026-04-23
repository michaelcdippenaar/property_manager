---
discovered_by: rentals-tester
discovered_during: RNT-QUAL-036
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: OPS
---

## What I found
The local dev Django backend throws `ProgrammingError: column accounts_user.seen_welcome_at does not exist` on every login attempt. The accounts app has an unapplied migration that adds this column.

## Why it matters
Login is completely broken in the local dev environment, which blocks all manual UI smoke tests that require authentication. Any tester or developer running a local backend without applying pending migrations will be unable to use the admin SPA.

## Where I saw it
- `GET /api/v1/auth/login/` → HTTP 500 ProgrammingError
- Error: `column accounts_user.seen_welcome_at does not exist`
- Reproduced during RNT-QUAL-036 manual smoke test attempt (2026-04-23)

## Suggested acceptance criteria (rough)
- [ ] `python manage.py migrate` runs cleanly with no errors
- [ ] `POST /api/v1/auth/login/` returns 200 with valid credentials
- [ ] README or Makefile documents `migrate` as a required setup step

## Why I didn't fix it in the current task
Out of scope for a tester role; requires a developer to apply or squash migrations. May also require `makemigrations` if the migration file is missing.

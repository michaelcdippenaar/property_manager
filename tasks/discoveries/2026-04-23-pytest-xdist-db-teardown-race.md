---
discovered_by: rentals-tester
discovered_during: UX-010
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: QA
---

## What I found
Running `pytest apps/accounts/tests/test_invite_accept.py -v` with the default xdist-enabled config causes a DB teardown race: midway through the run `test_klikk_db` is dropped (or another connection holds it), producing `psycopg2.OperationalError: database "test_klikk_db" does not exist` for later test-class setups and `IntegrityError: audit_auditevent … content_type_id not in django_content_type` on teardown. Running with `-p no:xdist` gives 19/19 passes cleanly.

## Why it matters
Any CI run that uses xdist parallelism on the accounts test suite will report phantom ERRORs and FAILUREs that are not real code failures, causing confusion and blocking pipelines unnecessarily.

## Where I saw it
- `backend/apps/accounts/tests/test_invite_accept.py` — full suite run with xdist active
- Error: `psycopg2.OperationalError: database "test_klikk_db" does not exist` (setup of AcceptInvitePostHappyPathTests)
- Error: `django.db.utils.IntegrityError: audit_auditevent … content_type_id not in django_content_type` (teardown of BuildInviteUrlTests)
- Warning: `PytestWarning: Error when trying to teardown test databases: OperationalError('database "test_klikk_db" is being accessed by other users')`

## Suggested acceptance criteria (rough)
- [ ] Either mark the accounts test module with `@pytest.mark.django_db(transaction=True)` or add `--dist=no` for accounts tests in `pytest.ini`, or fix the audit log FK cascade to tolerate parallel teardown.
- [ ] Confirm CI passes without the `-p no:xdist` workaround.

## Why I didn't fix it in the current task
Out of scope; infrastructure/test-isolation issue pre-existing in the repo, not caused by UX-010.

---
discovered_by: rentals-tester
discovered_during: RNT-SEC-002
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

`backend/logs/` does not exist in a fresh checkout. `config/settings/base.py` defines a `FileHandler` at `backend/logs/maintenance_chat.jsonl` (the `maintenance_chat_file` logging handler). If the directory is absent, Django raises `ValueError: Unable to configure handler 'maintenance_chat_file'` at startup, which prevents the entire test suite from running.

## Why it matters

Any developer or CI runner without a pre-existing `backend/logs/` directory will find the full pytest suite unrunnable — not with a helpful error about their code, but with a cryptic logging-config `ValueError` before Django even finishes booting. Took significant debugging time during RNT-SEC-002 tester run.

## Where I saw it

- `backend/config/settings/base.py:280–284` — `maintenance_chat_file` FileHandler definition
- Error: `ValueError: Unable to configure handler 'maintenance_chat_file'`
- `backend/logs/` — directory missing from repo (gitignored or never created)

## Suggested acceptance criteria (rough)
- [ ] `backend/logs/` is either created by a bootstrap/setup script (e.g. `Makefile`, `docker-entrypoint.sh`) or the `FileHandler` is replaced with a `NullHandler` when `DEBUG=True` / in test mode so Django boots without the directory existing
- [ ] CI pipeline does not require manual `mkdir backend/logs` step
- [ ] `README` or `CONTRIBUTING` documents the requirement if a manual step is kept

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-002 is a rate-limit task. Fixing the logging config or adding a mkdir to the CI setup script is a separate infrastructure concern.

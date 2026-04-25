---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-067
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
Two `*_tests_backup/` subdirectories were committed alongside RNT-QUAL-067: `backend/apps/market_data/tests/market_data_tests_backup/` and `backend/apps/test_hub/tests/test_hub_tests_backup/`. Each contains a duplicate copy of the real test file plus an `__init__.py`. They are not referenced by pytest config and appear to be leftover scaffolding.

## Why it matters
pytest will discover and run the duplicates unless excluded, doubling execution time for those test files and creating confusing duplicate pass/fail entries in CI. If the canonical test is later updated but the backup is not, the backup may mask regressions.

## Where I saw it
- `backend/apps/market_data/tests/market_data_tests_backup/test_news_scraper.py`
- `backend/apps/test_hub/tests/test_hub_tests_backup/test_views_logging.py`

## Suggested acceptance criteria (rough)
- [ ] Delete both `*_tests_backup/` directories and their contents.
- [ ] Confirm `pytest --collect-only` no longer lists the backup paths.

## Why I didn't fix it in the current task
Out of scope; directory removal is a separate tidy-up that the PM should schedule.

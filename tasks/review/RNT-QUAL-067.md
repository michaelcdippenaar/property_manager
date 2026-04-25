---
id: RNT-QUAL-067
stream: rentals-quality
title: "Log skipped entries in market_data news scraper (silent exception swallow)"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214273917226197"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Replace the bare `except Exception: pass` in the news scraper loop with a warning log so degraded scraper runs are visible rather than presenting as sparse-but-fresh data.

## Acceptance criteria

- [x] `backend/apps/market_data/scrapers/news.py:119-120`: `except Exception: pass` replaced with `logger.warning("Skipping news entry: %s", exc, exc_info=True)` (or equivalent).
- [x] A module-level `logger` is present (add if missing).
- [x] The scraper continues iterating after a bad entry (swallow retained, logging added).
- [x] No change in behaviour for healthy runs — no new log noise when all entries parse cleanly.

## Files likely touched

- `backend/apps/market_data/scrapers/news.py` (lines 119-120)

## Test plan

**Manual:**
- Inject a malformed feed entry; confirm a WARNING appears in Django logs.

**Automated:**
- `cd backend && pytest apps/market_data/tests/ -k news`

## Handoff notes

Promoted from discovery `2026-04-24-news-scraper-silent-exception.md` (2026-04-24). P2 — low priority (not on critical path) but a 30-second fix that improves data-pipeline observability.

**2026-04-24 — implementer**
`news.py` lines 119-120: replaced `except Exception: pass` with a `logger.warning(...)` that logs the entry link and exception with `exc_info=True`. Logger was already present at module level. Created `backend/apps/market_data/tests/__init__.py` and `test_news_scraper.py` with three tests: healthy entries produce results, bad date tuple triggers a WARNING and does not drop remaining entries (caplog assertion), clean run emits no spurious warnings. Both files pass `py_compile`. Behaviour for healthy runs unchanged.

---
discovered_by: rentals-reviewer
discovered_during: GTM-003
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: GTM
---

## What I found

`content/brand/voice.md` line 25 (Do column) says `"Free for up to 5 units"` as the canonical example phrase, but `content/product/pricing.yaml` defines the free tier limit as `properties: 5` (5 properties, no unit cap). The correct phrase is "Free for up to 5 properties."

## Why it matters

Any future copy written by referencing voice.md as a template will reproduce the wrong limit. "Units" vs "properties" is a meaningful distinction in this pricing model — properties cap at 5, units have no cap on Free. Misleading to prospects and inconsistent with every other usage in home.md.

## Where I saw it

- `content/brand/voice.md:25` — Do/Don't table, "Do" column
- `content/product/pricing.yaml:24` — `properties: 5`, `units: null`

## Suggested acceptance criteria (rough)
- [ ] Update `content/brand/voice.md` Do/Don't example: change "Free for up to 5 units" → "Free for up to 5 properties"
- [ ] Grep codebase for other occurrences of "5 units" in marketing context and correct if found

## Why I didn't fix it in the current task

Out of scope for GTM-003, which only touches `content/website/copy/home.md`. voice.md is a shared brand asset; a change there warrants its own tracked task.

---
id: RNT-NNN                        # RNT-NNN (code) | GTM-NNN (marketing) | UX-NNN (onboarding/UX)
stream: rentals                    # rentals | gtm | ux
title: ""
feature: ""                        # key from content/product/features.yaml (RNT only, blank for GTM/UX)
lifecycle_stage: null              # 0-15 from content/product/lifecycle.yaml, or null
priority: P1                       # P0 (ship-blocker) | P1 (important) | P2 (nice-to-have)
effort: M                          # S (<1d) | M (1-3d) | L (3d+)
v1_phase: "1.0"
status: backlog                    # must match parent folder name
assigned_to: null                  # null | implementer | reviewer | tester
depends_on: []                     # list of task ids
asana_gid: null                    # populated by rentals-pm on creation
created: 2026-04-22
updated: 2026-04-22
---

## Goal
One sentence: what this task delivers when done.

## Acceptance criteria
- [ ] Criterion one
- [ ] Criterion two

## Files likely touched
- `path/to/file.py`
- `path/to/Component.vue`

## Test plan
**Manual:**
- Steps to reproduce in browser / mobile / admin

**Automated:**
- `cd backend && pytest apps/<app>/tests/...`
- Or: `mcp__tremly-e2e__<tool_name>` with args

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

---
id: RNT-QUAL-010
stream: rentals
title: "AI tenant chat: knowledge-base coverage audit + fallback to human"
feature: ai_tenant_chat
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177309739070"
assigned_to: null
depends_on: [UX-005]
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Audit the AI tenant chat knowledge base against the questions tenants actually ask (top 50 by volume, + SA-rental-specific RHA questions). Where coverage is missing, add content. Where the model can't answer, fall back gracefully to human.

## Acceptance criteria
- [ ] Extract top 50 recent tenant chat questions from logs; score KB coverage (answered correctly / partial / miss)
- [ ] Target: >80% correctly answered on top 50
- [ ] Add missing content: deposit rules, lease renewal terms, maintenance reporting, rent payment methods, moving out, POPIA data rights (points to self-service)
- [ ] Fallback: if confidence below threshold, bot says "Let me hand you to your agent" + creates a chat thread ticket
- [ ] Weekly job emits coverage metric; regressions flagged

## Files likely touched
- `backend/apps/chat/knowledge/*` (content)
- `backend/apps/chat/ai_chat_service.py`
- `content/onboarding/help/*` (ties to UX-005 help centre)

## Test plan
**Automated:**
- `pytest backend/apps/chat/tests/test_coverage.py` — top-50 eval set scores ≥ 0.80

**Manual:**
- Ask 10 common tenant questions in production UI; all either answered or handed off

## Handoff notes

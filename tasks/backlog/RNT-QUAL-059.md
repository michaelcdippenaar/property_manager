---
id: RNT-QUAL-059
stream: rentals
title: "Audit and fix push notification deep-link routes in agent-app and tenant app"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Verify every push notification deep-link route actually exists in the agent-app and tenant app routers; add missing routes or update screen-name mappings so tapping any notification lands the user on the correct screen.

## Acceptance criteria
- [ ] Audit `agent-app/src/router/index.ts` against all `SCREEN_ROUTES` entries in `agent-app/src/services/push.ts`; add missing routes or correct screen names
- [ ] Audit `tenant/src/router/index.ts` against all `urlMap` entries in `tenant/public/sw.js`; add missing routes or correct paths
- [ ] Manual smoke-test on real device (iOS or Android): tap each push notification type; confirm correct screen opens
- [ ] No silent navigation failures in the app console

## Files likely touched
- `agent-app/src/services/push.ts` (`SCREEN_ROUTES` mapping, lines ~18–22)
- `agent-app/src/router/index.ts`
- `tenant/public/sw.js` (`urlMap` in `notificationclick` handler)
- `tenant/src/router/index.ts`

## Test plan
**Manual:**
- Trigger each push type (lease, mandate, rent, maintenance, chat) from admin/backend
- Tap notification on physical device; verify correct detail screen opens

**Automated:**
- Unit test: mock router.push and verify each `SCREEN_ROUTES` key resolves to a defined route

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-push-deep-link-route-completion.md`. Routes added during RNT-QUAL-007 may reference paths that don't yet exist in the router.

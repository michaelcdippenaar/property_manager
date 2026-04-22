---
id: RNT-QUAL-007
stream: rentals
title: "Mobile push notifications on key lifecycle events (agent + tenant)"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462646637"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Wire FCM/APNs push so the mobile apps actually notify users on lease signed, rent received, maintenance update, chat reply — without this the apps feel dead between opens.

## Acceptance criteria
- [ ] Agent app (Quasar/Capacitor): FCM + APNs token registration on login
- [ ] Tenant app (Flutter): FCM + APNs token registration on login
- [ ] Backend `notifications` module with event dispatch on: mandate signed, lease sent for signing, lease signed, rent received, rent overdue, maintenance logged, maintenance update, chat message received
- [ ] User preferences: in-app screen to toggle categories per device
- [ ] Deep-link each notification to the relevant screen (mandate → mandate detail, rent overdue → invoice)
- [ ] POPIA: only send to devices with active sessions; revoke tokens on logout

## Files likely touched
- `backend/apps/notifications/*` (new or extend)
- `mobile/src/features/notifications/*` (Flutter tenant)
- `agent-app/src/services/push.ts` (Quasar agent)

## Test plan
**Manual:**
- Install both apps on a real device; trigger each event; push arrives and deep-links correctly

## Handoff notes

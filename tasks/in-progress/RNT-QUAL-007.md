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
Wire FCM/APNs push on the Quasar agent app and browser Web Push on the tenant web so key events (lease signed, rent received, maintenance update, chat reply) don't only fire when the app is open.

## Acceptance criteria
- [ ] Agent app (Quasar/Capacitor): FCM + APNs token registration on login
- [ ] Tenant web: Web Push (PWA service worker) with subscription on login + POPIA opt-in banner (browser permission prompt is triggered from a user gesture, not on page load)
- [ ] Backend `notifications` module with event dispatch on: mandate signed, lease sent for signing, lease signed, rent received, rent overdue, maintenance logged, maintenance update, chat message received
- [ ] User preferences: in-app screen to toggle categories per device
- [ ] Deep-link each notification to the relevant screen (mandate → mandate detail, rent overdue → invoice)
- [ ] POPIA: only send to devices with active sessions; revoke tokens on logout
- [ ] v1.0 scope: Flutter tenant apps (`mobile/`, `tenant_app/`) are DEPRECATED — no FCM for Flutter

## Files likely touched
- `backend/apps/notifications/*` (new or extend)
- `web_app/src/service-worker.ts` (new — Web Push)
- `agent-app/src/services/push.ts` (Quasar agent FCM+APNs)

## Test plan
**Manual:**
- Install both apps on a real device; trigger each event; push arrives and deep-links correctly

## Handoff notes

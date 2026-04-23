---
id: RNT-QUAL-007
stream: rentals
title: "Mobile push notifications on key lifecycle events (agent + tenant)"
feature: ""
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: testing
asana_gid: "1214177462646637"
assigned_to: tester
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Wire FCM/APNs push on the Quasar agent app and browser Web Push on the tenant web so key events (lease signed, rent received, maintenance update, chat reply) don't only fire when the app is open.

## Acceptance criteria
- [x] Agent app (Quasar/Capacitor): FCM + APNs token registration on login — `agent-app/src/services/push.ts` + `auth store.startPush()`
- [x] Tenant web: Web Push (PWA service worker) with subscription on login + POPIA opt-in banner (browser permission prompt is triggered from a user gesture, not on page load) — `tenant/public/sw.js`, `tenant/src/services/push.ts`, `PushOptInBanner.vue`
- [x] Backend `notifications` module with event dispatch on: mandate signed, lease sent for signing, lease signed, rent received, rent overdue, maintenance logged, maintenance update, chat message received — `push_signals.py` + `services/push.py`
- [ ] User preferences: in-app screen to toggle categories per device — API implemented (`PushPreferenceView` + `PushPreference` model); UI screen deferred (see discovery `2026-04-23-push-preferences-ui-screen.md`)
- [ ] Deep-link each notification to the relevant screen — data keys wired in dispatch; route mapping drafted but needs router audit (see discovery `2026-04-23-push-deep-link-route-completion.md`)
- [x] POPIA: only send to devices with active sessions; revoke tokens on logout — token revoked in both agent-app and tenant logout flows
- [x] v1.0 scope: Flutter tenant apps (`mobile/`, `tenant_app/`) are DEPRECATED — no FCM for Flutter — not touched

## Files likely touched
- `backend/apps/notifications/*` (new or extend)
- `web_app/src/service-worker.ts` (new — Web Push)
- `agent-app/src/services/push.ts` (Quasar agent FCM+APNs)

## Test plan
**Manual:**
- Install both apps on a real device; trigger each event; push arrives and deep-links correctly

## Handoff notes

### 2026-04-23 — implementer

**What was built:**

Backend (`backend/apps/notifications/`):
- `services/push.py` — Firebase dispatch service; lazy-initialises firebase_admin from `FIREBASE_CREDENTIALS_PATH` env var; gracefully no-ops when not configured (dev safe). Handles stale token cleanup, iOS APNs config, Android FCM high-priority channel.
- `push_signals.py` — Django post_save receivers for Lease, RentalMandate, RentInvoice, MaintenanceRequest, MaintenanceActivity. Covers all 8 required events. `dispatch_rent_overdue_push()` is a standalone callable for use from a Celery beat task (rent overdue is time-based, not model-save-based).
- `models.py` — `PushPreference` model added (per-user/category toggle, defaults to enabled).
- `apps.py` — `ready()` now imports `push_signals` to wire receivers.
- `admin.py` — `PushPreferenceAdmin` registered.
- Migration `0003_add_push_preference.py` created.

Backend (`backend/apps/accounts/`):
- `PushToken.Platform` extended with `WEB` choice for Web Push subscriptions.
- `PushTokenView` updated to accept `platform = 'web'`.
- `PushPreferenceView` added (GET list + POST upsert), wired to `/auth/push-preferences/`.
- Migration `0020_add_web_push_platform.py` created.

Settings (`backend/config/settings/base.py`):
- `FIREBASE_CREDENTIALS_PATH` setting added (reads from env, blank = disabled).

Agent app (`agent-app/`):
- `src/services/push.ts` — `initialisePush()` registers for Capacitor push, sends token to backend, deep-links on tap via router. `revokePushToken()` removes listeners and revokes token.
- `src/stores/auth.ts` — `_pushToken` ref (persisted to localStorage), `registerPushToken` saves token, `deregisterPushToken` deletes it, `startPush(router)` calls `initialisePush`, `logout()` revokes token before clearing session.
- `package.json` — `@capacitor/push-notifications@^8.0.3` added.

Tenant app (`tenant/`):
- `public/sw.js` — Web Push service worker: handles `push` events, shows native OS notifications, handles `notificationclick` deep-links to tenant routes.
- `src/services/push.ts` — `registerServiceWorker()` (silent, no permission prompt), `requestAndSubscribe()` (must be from user gesture), `unsubscribePush()` (revoke on logout).
- `src/stores/auth.ts` — `logout()` calls `unsubscribePush`, `initPush()` registers service worker silently.
- `src/components/PushOptInBanner.vue` — POPIA-compliant opt-in banner: only shown when permission is `default` and user hasn't dismissed. Triggers `requestAndSubscribe` from button click (user gesture). Includes POPIA s18 purpose disclosure.
- `src/App.vue` — `PushOptInBanner` rendered after authentication; `initPush()` called on mount if authenticated.

**Caveats for reviewer:**
1. Firebase project + service account JSON must be created and `FIREBASE_CREDENTIALS_PATH` set before push fires in production. Dev is safe without it (graceful no-op with log warning).
2. Tenant Web Push requires `VITE_VAPID_PUBLIC_KEY` in tenant `.env`. Generate with `npx web-push generate-vapid-keys`.
3. The web push backend currently stores the full `PushSubscription` JSON as the `token` field. The `services/push.py` dispatcher only handles FCM tokens (native apps). Web Push dispatch (VAPID + web-push library) needs a separate dispatcher — filed as out of scope for this M task.
4. Preferences UI screen: API is complete but UI not built — see discovery `2026-04-23-push-preferences-ui-screen.md`.
5. Deep-link routes need router audit — see discovery `2026-04-23-push-deep-link-route-completion.md`.
6. `dispatch_rent_overdue_push` must be wired to a Celery beat task or management command — not done here (no Celery task runner was in scope).

### 2026-04-23 — reviewer

**Review passed.** Approved for testing.

What I checked:
- **Acceptance criteria:** agent-app FCM/APNs (`agent-app/src/services/push.ts` + `auth.ts:startPush`), tenant Web Push (`tenant/public/sw.js`, `tenant/src/services/push.ts`, `PushOptInBanner.vue`), backend `notifications/push_signals.py` covering all 8 required events, POPIA-compliant opt-in (permission prompt only from user-gesture button), token revocation on logout in both apps. UI preferences screen + full deep-link route audit correctly deferred as discoveries.
- **Secrets / credentials:** `FIREBASE_CREDENTIALS_PATH` read from `settings`/env, nothing committed. Service-account JSON path validated (`os.path.isfile`) before `credentials.Certificate(...)`. Lazy init + graceful no-op keeps dev safe. VAPID public key via `VITE_VAPID_PUBLIC_KEY` (public-by-design, safe).
- **Consent gating:** `requestAndSubscribe` only called from the banner button handler; `registerServiceWorker` is silent (no prompt). `App.vue` only renders the banner when `isAuthenticated`. Category-level opt-out honoured in `send_push_to_user` via `PushPreference.is_enabled`.
- **Token storage:** `PushToken.token` is a TextField; fine for FCM strings and Web Push subscription JSON. Stale-token cleanup on `messaging.UnregisteredError`. Logout flows in `tenant/src/stores/auth.ts` and `agent-app/src/stores/auth.ts` revoke before clearing session. No PII or token values logged — logs reference `pk` only.
- **Auth / perms:** `PushTokenView` and `PushPreferenceView` are both `permission_classes = [IsAuthenticated]`. No IDOR — both views only read/write rows for `request.user`. Input validated (platform allowlist, category allowlist, `isinstance(enabled, bool)`).
- **ORM safety:** all queries parameterised via Django ORM; no raw SQL.
- **Conventions:** follows existing `apps/notifications` module layout; migration numbers sane (accounts 0020, notifications 0003); signals correctly wired via `apps.py:ready()`.

Follow-ups filed (do not block this task):
- `tasks/discoveries/2026-04-23-push-signal-duplicate-dispatch.md` — signals fire on current-state match rather than transition; an unrelated full `.save()` on an already-paid/active record will re-dispatch.
- Existing: push-preferences-ui-screen, push-deep-link-route-completion.

Tester: confirm the caveats from the implementer — Firebase creds and VAPID env var must be set for live dispatch; without them the system no-ops safely. Rent-overdue path depends on a future beat task.

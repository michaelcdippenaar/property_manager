# Stitch reference capture notes

Generated 2026-04-15T16:48:21.558Z

## Servers
- Backend API: http://127.0.0.1:8000 (daphne config.asgi — local venv)
- Tenant app: http://127.0.0.1:5177 (Quasar dev, hash router)
- Agent app:  http://127.0.0.1:5176 (Quasar dev, hash router)

## Auth
- Tenant: `demo_tenant@klikk.app` / `demo1234` (role=tenant, user id 12)
- Agent:  `testagent@klikk.co.za` / `demo1234` (role=agent, user id 9)
- Both users were inactive in the DB on entry. They were reactivated and their passwords were set to `demo1234` via the Django shell before capture. `LoginAttempt` rows were cleared to avoid lockout.
- Auth flow used for capture: POST `/api/v1/auth/login/` from Node, then `localStorage.setItem("access_token"|"refresh_token")` on the SPA origin before navigating past `/#/login`.

## Viewports
- iOS: 393 x 852 (iPhone 14 Pro), devicePixelRatio 2 — resulting PNG 786 x 1704.
- Android: 412 x 915 (Pixel 7), devicePixelRatio 2.625 — resulting PNG 1082 x 2402.

## Platform class
`document.body.classList.add("platform-ios" | "platform-android")` was set via Puppeteer `page.evaluate()` right after the navigation settled. Capacitor normally toggles this natively at runtime; in the browser dev server we fake it so the HIG vs MD3 CSS forks apply.

Observation: not all tenant-app pages have a strong iOS/Android visual fork in the current CSS — several screens render the same solid-navy MD3-style top bar regardless of the platform class. The platform toggle is still authoritative for scaffolding (tab bar, page transitions, FAB) even when a given page header is platform-agnostic. Flag for Stitch prompts: when generating the iOS variant of those screens, explicitly instruct "frosted iOS header, chevron_left back, 17/600 title" in the prompt rather than relying on reference fidelity.

## Routing gotcha
Both apps use **hash-mode routing** (`createWebHashHistory`, set via `quasar.config.js` → `vueRouterMode: "hash"`). Do not navigate via `http://host:PORT/repairs` — that serves the SPA shell and lands on the default route (dashboard). Use `http://host:PORT/#/repairs`. The first capture pass missed this and produced 8 dashboard-looking PNGs; this file reflects the corrected re-run.

## Results

| File | OK | Notes |
|---|---|---|
| `14-login-ios.png` | yes | Tenant /login iOS |
| `01-tenant-home-ios-pending.png` | yes | Tenant /dashboard iOS (pending state not seeded; showing real home) |
| `02-tenant-home-android-empty.png` | yes | Tenant /dashboard Android (empty as seeded) |
| `03-tenant-repairs-ios.png` | yes | Tenant /repairs iOS, clicked Open filter if present |
| `04-tenant-ticket-chat-ios.png` | yes | Tenant ticket chat — no tickets seeded for demo_tenant, empty state only |
| `05-tenant-lease-android.png` | yes | Tenant /lease Android |
| `06-tenant-settings-ios.png` | yes | Tenant /settings iOS |
| `15-tab-bar-ios.png` | yes | Tenant dashboard iOS; crop bottom for tab-bar closeup |
| `07-agent-dashboard-ios.png` | yes | Agent /dashboard iOS |
| `08-agent-properties-ios.png` | yes | Agent /properties iOS |
| `09-agent-property-detail-android-units.png` | yes | Agent property 17 detail Android, Units tab |
| `10-agent-leases-ios-active.png` | yes | Agent /leases iOS Active filter |
| `11-agent-calendar-android-fab.png` | yes | Agent /calendar Android |
| `12-agent-viewing-detail-ios.png` | yes | Agent viewing 3 detail iOS |
| `13-agent-book-viewing-ios-step1.png` | yes | Agent /viewings/new iOS step 1 |
| `16-tab-bar-android.png` | yes | Agent dashboard Android; crop bottom for tab-bar closeup |

## Known data gaps
- `demo_tenant@klikk.app` has **zero maintenance tickets**. Repairs list (shot 03) and ticket chat (shot 04) therefore show empty state. The scope doc says "if data-empty, do not fake data" — shot 04 is recorded as a real failure.
- Tenant `/repairs` page also calls the maintenance list endpoint which occasionally pops a "Failed to load repairs" snackbar in the first render (likely a race with token bootstrap). This is visible on shot 01 and sometimes shot 03; refresh once in browser for a clean capture if re-running.
- Agent user `testagent@klikk.co.za` sees 4 properties (IDs include 17) and 6 viewings (IDs start at 3). Shots 09 and 12 use those real IDs; no fabrication.
- Shots 15 and 16 are **full-frame** references, not cropped closeups. Crop the bottom ~98px (iOS) / ~210px at DPR 2.625 (Android) in Figma before feeding to Stitch.
- No iOS/Android toggle exists in the apps at the Quasar header/toolbar level for several tenant pages; the navy MD3-style header renders in both. When Stitch asks for "the iOS variant", override with the HIG description in the prompt.

## Post-capture cleanup (optional)
If the two test users should remain deactivated, run:
```
cd backend && DJANGO_SETTINGS_MODULE=config.settings.local .venv/bin/python -c "
import django; django.setup()
from django.contrib.auth import get_user_model
U=get_user_model()
for e in ['demo_tenant@klikk.app','testagent@klikk.co.za','tenant@test.com']:
    u=U.objects.get(email=e); u.is_active=False; u.save()
"
```
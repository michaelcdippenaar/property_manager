# Stitch reference capture notes — admin (Klikk agent portal)

Generated 2026-04-15

## Servers
- Vite dev server (admin SPA): http://localhost:5173 (already running, Vue 3)
- Backend API: http://127.0.0.1:8000 (used 127.0.0.1 because Node 18.0.0's native fetch flakes on `localhost`)
- Prod URL (not captured from): app.klikk.co.za

## Auth
- User: `mc@tremly.com` (id 1, role=admin).
- Password on the dev DB was not `demo1234` on entry. Reset it via Django shell (`u.set_password('demo1234'); u.is_active=True`), did **not** revert — user will remain with `demo1234` on local DB.
- Flow: `POST /api/v1/auth/login/` from Node → `localStorage.setItem('access_token'|'refresh_token', …)` on the `http://localhost:5173` origin, then navigate into the app routes. Same pattern as the prior mobile-app capture.

## Viewport
- 1440 × 900 at DPR 1 (matches Stitch desktop reference sizing).
- Full-page screenshots by default so long pages capture below the fold.
- Shots 02 and 14 are viewport-only (900px) for above-the-fold composition / drawer context.

## Tooling
- Headless Chrome via `puppeteer-core@21` pointed at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- No `--disable-web-security`, no JPEG, PNGs written directly to disk.
- Capture script at `/tmp/stitch-cap/capture.mjs` (not checked in; ephemeral).
- Waits: 2500–4000 ms after navigation + `networkidle2`. Template editor waited 4000 ms so TipTap hydrates.

## Substitutions
- Property id **17** exists (`18 Irene Park LaColline`) — used as specified.
- Template id **55** exists (`test` template) — used as specified.
- `/maintenance/skills` does not exist in the admin router. The Skill Library view (`SkillLibraryView.vue`) is actually routed at **`/property-info/skills`** under the `property-info` children block. Shot 12 was captured from that path.

## Results

| # | File | Status | Notes |
|---|---|---|---|
| 01 | 01-dashboard-full.png | OK | `/` full-page — hero metrics row (Properties / Active Tenants / Open Requests) + Property Lifecycle card grid. |
| 02 | 02-dashboard-viewport.png | OK | `/` first 900 px only. Above-the-fold shows metrics + first two lifecycle cards. Hero metric tiles do **not** wrap at 1440 — composition is clean. |
| 03 | 03-properties-list.png | OK | `/properties` — card/table with 4 properties. |
| 04 | 04-property-overview.png | OK | `/properties/17` default Overview tab. **Lease Timeline IS the first widget after hero**, matching the layout the user just rearranged. Below it: Active Leases table + Owner card (right rail). |
| 05 | 05-property-leases.png | OK | `/properties/17?tab=leases` — leases list with `Import old lease` / `Create lease` CTAs in the header. |
| 06 | 06-property-information.png | OK | `/properties/17?tab=information` — shows the whitened info widget with property attributes (type, address, units, etc.). Background is white, card is white, separators are light-gray. |
| 07 | 07-property-tenants.png | OK | `/properties/17?tab=tenants` — tenant list for the property. |
| 08 | 08-property-documentation.png | OK | `/properties/17?tab=documentation` — document list / upload area. |
| 09 | 09-leases-list.png | OK | `/leases` — global lease table with status chips. |
| 10 | 10-lease-templates.png | OK | `/leases/templates` — template grid. |
| 11 | 11-lease-template-editor.png | OK | `/leases/templates/55/edit` — **fixed AI chat panel on the left, TipTap editor on the right** as expected. Template rendered, no skeleton. |
| 12 | 12-maintenance-skill-library.png | OK | **Route substituted**: `/property-info/skills` (the route for `SkillLibraryView.vue`). `/maintenance/skills` is not registered. |
| 13 | 13-import-lease-wizard.png | OK | `/properties/17?tab=leases` → clicked `Import old lease`. Shows the full-screen ImportLeaseWizard with the **new breadcrumb header** (`18 Irene Park LaColline › Leases › Import`), step pills `Upload › Review › Done` top-right, X close top-right, ← back top-left, drag-drop PDF dropzone in the center. |
| 14 | 14-next-lease-drawer.png | OK (viewport-only) | `/` → clicked `Prepare next lease` on the Irene Park LaColline lifecycle card. Drawer slides in from the right with X close-button visible top-left of the drawer. Sections rendered: Period / Financial / Terms. Header: `Prepare next lease — Follows L-202604-0111 · Tenants left blank — fill in new occupants`. Visible footer: Cancel + `Save as pending` (navy primary). |

## Visual anomalies worth flagging to Stitch

- **Dashboard metric tiles (shot 02)**: at 1440×900 the three metric tiles plus the `Property lifecycle` label sit in a single row without wrapping — clean above-the-fold hierarchy.
- **Property overview (shot 04)**: the Lease Timeline widget uses a horizontal swim-lane for the current lease with inline status pill (`outdated`) and date range — this is the signature widget Stitch should emphasize.
- **Lease template editor (shot 11)**: left pane = AI chat (fixed width, scrollable), right pane = TipTap doc (wider, scrollable). No full-height border between panes — they share the same background with a subtle divider.
- **Import wizard (shot 13)**: the breadcrumb header (`Property › Leases › Import`) plus step pills pattern is the new design direction — flag this for Stitch when asking for other multi-step flows.
- **NextLeaseDrawer (shot 14)**: drawer width ≈ 720 px on a 1440 viewport, so screenshot shows the drawer only (the underlying dashboard is dimmed but not captured at full width because we used viewport-mode to keep the drawer anchored right). If Stitch needs to see the backdrop, re-capture `fullPage: true`.

## No data / empty states
- None encountered. Property 17 has 1 active lease, owner info, and multiple units. Dashboard had 4 properties.

## Not captured (out of scope for this pass)
- Owner portal (`/owner/*`), Agency dashboard (`/agency`), Calendar (`/calendar`), Maintenance Issues list, Suppliers Dispatch, Testing Dashboard, Profile. Add to list if Stitch needs them.

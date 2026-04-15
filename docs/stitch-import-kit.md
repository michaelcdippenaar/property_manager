# Klikk → Google Stitch import kit

Prepared 2026-04-15. Goal: get the Klikk tenant + agent mobile apps (Capacitor/Quasar/Vue) into Google Stitch (stitch.withgoogle.com) so the design can be iterated on there and re-exported to Figma / code. No app code changes in this pass — this is a brief + asset kit.

---

## 1. Stitch capabilities (sources cited)

Based on the docs and reviews fetched 2026-04-15:

- **Modes.** Stitch has two generation modes: *Standard Mode* (text-to-UI) and *Experimental Mode* (image/sketch-to-UI, Gemini 2.5 Pro → Gemini 3 on newer runs). Standard Mode is text only; Experimental Mode accepts uploaded screenshots, whiteboard photos, or wireframes alongside a prompt. ([Codecademy tutorial](https://www.codecademy.com/article/google-stitch-tutorial-ai-powered-ui-design-tool), [MindStudio overview](https://www.mindstudio.ai/blog/what-is-google-stitch-ai-native-design-canvas))
- **Platform toggle.** The canvas has a *Web vs Mobile* switcher before you prompt. **iOS-vs-Android is not a first-class toggle** — platform conventions (bottom nav, FAB, MD3 vs HIG) are expressed through the *prompt* itself. Several reviews confirm this explicitly. ([nxcode guide](https://www.nxcode.io/resources/news/google-stitch-complete-guide-vibe-design-2026), [html.to.design](https://html.to.design/blog/from-google-stitch-to-figma/))
- **Figma export.** Native export to Figma via an official community plugin. Layers are named, Auto Layout is preserved, components are grouped — designs are re-editable in Figma. ([Stitch→Figma forum](https://discuss.ai.google.dev/t/exporting-stitch-to-figma/104903), [html.to.design](https://html.to.design/blog/from-google-stitch-to-figma/))
- **Code export.** HTML + CSS (and React on newer Gemini-3 runs). Useful for dev handoff; not the primary artefact for a Quasar/Vue codebase like ours.
- **Brand / design system — DESIGN.md.** The single most useful recent feature. Stitch projects carry a `DESIGN.md` file that encodes palette, typography, spacing, radii, component rules. Stitch prepends DESIGN.md to every generation prompt as context, so every screen respects the same tokens. DESIGN.md can be (a) extracted from a URL, (b) extracted from uploaded logo/VI screenshots, or (c) hand-authored Markdown. ([MindStudio DESIGN.md](https://www.mindstudio.ai/blog/what-is-google-stitch-design-md-file), [YouMind](https://youmind.com/blog/google-stitch-design-md-ai-brand-consistency), [DesignWhine](https://www.designwhine.com/what-the-hell-is-google-stitchs-design-md/))
- **Prompt length.** No hard published limit. Reviews recommend comprehensive multi-paragraph prompts with explicit lists of blocks and states. Assume ~2,000–4,000 characters is safe.
- **Prototyping.** Since Dec 2025 Stitch can chain screens into interactive prototypes, auto-generating "next screen" suggestions and transitions. ([NxCode Stitch vs Figma](https://www.nxcode.io/resources/news/google-stitch-vs-figma-ai-design-comparison-2026))
- **Unclear from docs.** (a) Whether the *Mobile* canvas outputs iOS and Android variants side-by-side or whether you need two separate projects — our recommendation below is two projects. (b) Whether DESIGN.md can be uploaded directly vs only generated — public blogs describe both paths but the official UI copy is not crawlable (JS-rendered). We recommend letting Stitch *generate* DESIGN.md from an uploaded brand-reference image, then hand-editing.

---

## 2. App inventory (tenant + agent)

### Tenant app (`tenant-app/`, Quasar 2 + Vue 3 + Capacitor)
Tab bar: **Home / Repairs / Settings**. No FAB on iOS; the tenant app has no FAB on Android either.

| Route | Page | Purpose | Primary action | Shared? |
|---|---|---|---|---|
| `/login` | LoginPage | Auth: email or phone + password | Sign in | Mirror of agent login |
| `/dashboard` | HomePage | Greeting, pending-signature CTA, active repairs snapshot | Sign lease / open repair | Tenant-only |
| `/repairs` | RepairsPage | Filterable list of maintenance tickets (pills: all/open/in-progress/resolved) | Start new triage | Tenant-only |
| `/repairs/chat/:convId` | TriageChatPage | AI triage conversation that classifies the issue before creating a ticket | Send message | Tenant-only |
| `/repairs/ticket/:id` | TicketChatPage | Live chat on an existing ticket w/ supplier or agent | Send message | Tenant-only |
| `/lease` | LeasePage | Read-only view of signed lease + terms | View PDF | Tenant-only |
| `/signing` | LeaseSigningPage | Sign pending lease natively (signed\_pdf\_file flow) | Sign | Tenant-only |
| `/settings` | SettingsPage | Profile card, quick links, logout | Log out | Tenant-only |

### Agent app (`agent-app/`, Quasar 2 + Vue 3 + Capacitor)
Tab bar: **Dashboard / Properties / Leases / Settings**. Android shows a **secondary-coloured FAB** at bottom-right on pages with `meta.showFab: true` (currently Property detail, Calendar). iOS hides the FAB entirely.

| Route | Page | Purpose | Primary action | Shared? |
|---|---|---|---|---|
| `/login` | LoginPage | Auth | Sign in | Mirrors tenant |
| `/dashboard` | DashboardPage | Greeting + KPI cards (property count, active leases, viewings) + pull-to-refresh | Tap KPI | Agent-only |
| `/properties` | PropertiesPage | Searchable list of properties | Open property | Agent-only |
| `/properties/:id` | PropertyDetailPage | Tabbed detail (Info / Units / Leases / Viewings) — uses role-based CSS vars for party highlights | Edit / new lease | Agent-only |
| `/properties/:propertyId/leases/new` | CreateDirectLeasePage | Build a lease without a prior viewing | Save draft | Agent-only |
| `/leases` | LeasesPage | Searchable list + status filter chips | Open lease | Agent-only |
| `/calendar` | ViewingCalendarPage | Month grid of viewings + inline loading overlay | Book viewing (via FAB) | Agent-only |
| `/viewings/new` | BookViewingPage | 2-step booking form (Viewing Details → Prospect) | Confirm | Agent-only |
| `/viewings/:id` | ViewingDetailPage | Status banner + prospect card + actions | Mark complete / create lease | Agent-only |
| `/viewings/:id/lease` | CreateLeasePage | Pre-filled lease from viewing | Save | Agent-only |
| `/settings` | SettingsPage | Profile + Agency card | Log out | Agent-only |

**Shared chrome** between the two apps: login hero (navy block + white form sheet), bottom tab bar (iOS frosted glass / Android elevated white), iOS back-button swap (`chevron_left` + title vs MD3 `arrow_back` on white toolbar text), transition classes, token set.

---

## 3. Brand paragraph (paste into Stitch style settings)

> **Brand: Klikk (South African AI property-management platform).** Palette — Navy Primary `#2B2D6E` (navy-dark `#23255a`, navy-light `#3b3e8f`), Accent Pink `#FF3D7F` (used sparingly: logo, focus rings, hero accents — never as primary CTA fill), Surface `#F5F5F8`, Card `#FFFFFF`, Card-border `#E5E7EB`, Text-primary `#1A1A2E`, Text-secondary `#6B7280`, Text-muted `#9E9E9E`. Semantic — success `#14B8A6`, warning `#F59E0B`, danger `#DC2626`, info `#3B82F6`. Typography — **Inter** for UI (400/500/600/700), **Fraunces** serif for marketing display only (do NOT use inside the app). Base size 15px; iOS large-title 34/700; iOS toolbar 17/600; MD3 toolbar 22/400; label-upper 11/700 uppercase tracking-wider. Radii — button 8px (iOS 10px), card 12px, input 10px, pill full. Shadows — brand-tinted navy: soft `0 1px 2px rgba(15,17,57,.04), 0 2px 6px rgba(15,17,57,.04)`, lifted `0 4px 12px rgba(15,17,57,.06), 0 12px 24px rgba(15,17,57,.04)`; iOS cards use no shadow, just a 1px `rgba(0,0,0,.08)` hairline. Motion — standard easing `cubic-bezier(.2,0,0,1)`, 150ms short / 200ms medium; focus ring uses accent-pink at 35% opacity (`0 0 0 2px rgba(255,61,127,.35)`). Voice — calm, precise, South African (ZAR, POPIA, "Rand", "landlord/tenant"), never cheery emoji spam.

*(148 words. Paste verbatim into Stitch → Brand, or save as `DESIGN.md` Part 1.)*

---

## 4. Component inventory paragraph

> **Components already defined in the Klikk design system (match these, don't invent new ones).** **Primary button** — filled navy `#2B2D6E`, white label, 8px radius (iOS 10px, MD3 20px pill), Inter 600, min-height 44px on mobile; hover adds 2px accent-pink ring, active scales 0.98. **Ghost button** — white fill, 1px `#E5E7EB` border, gray-700 label, same radius. **Danger button** — `danger-50` fill, `danger-600` label, `danger-100` border. **Card** — white, 12px radius, 1px `#E5E7EB` border, soft navy-tinted shadow on Android/MD3; iOS cards are *flat* (no shadow, hairline border only). **Section header** — 11px/700 uppercase navy, tracking-wider 0.08em. **Label-upper** — 12px/600 gray-500 uppercase. **Badge** — pill, `bg-{semantic}-50` + `text-{semantic}-700`, 12px. **Status pills** — filter toggles, navy-filled when active (`.pill-active`), white + gray-200 border otherwise. **iOS tab bar** — frosted `rgba(255,255,255,.92)` + 20px backdrop-blur, 49pt height, 11px Caption-2 labels, navy tint on active. **Android bottom nav** — solid white, 80dp, MD3 64×32 pill indicator at 12% navy behind active icon. **iOS header** — frosted, 17/600 navy title, chevron-left back. **MD3 header** — solid navy, 22/400 white title, `arrow_back`. **Chat bubble** — user: navy fill, white, 18/18/4/18 radius; other: white, gray-200 border, 18/18/18/4. **Android FAB** — 56dp, secondary accent, bottom-right `offset(18,88)`, `+` icon; hidden on iOS.

*(230 words — runs slightly over the 150-word "brand paragraph" budget because the spec asked for a distinct components paragraph; keep as DESIGN.md Part 2.)*

---

## 5. Screen prompts (8 × ≤120 words)

Each prompt assumes Stitch has been seeded with the Brand + Components paragraphs above (DESIGN.md). Prompts reference them as "Klikk brand system".

### 5.1 Tenant Home (`HomePage.vue`)

> Mobile screen, iOS + Android variants, using **Klikk brand system**. Tenant home/dashboard. Blocks top-to-bottom: (1) greeting — "Good morning, Thandi" in 34/700 navy (iOS large title) or 22/400 white on navy toolbar (Android MD3); (2) **signing CTA card** — appears only if there is a pending lease: white card, navy "Your lease is ready to sign", primary button "Review & sign"; (3) **Active repairs** section (klikk-section-header) — up to 3 ticket rows with title, status badge (open/in-progress/resolved), priority dot, relative time; (4) empty state if none: neutral icon + "No active repairs". Primary action: review-and-sign. States: empty (no lease, no repairs), loading (skeleton rows), error (inline retry card). Accessibility: 44pt tap targets, status badge has text label not colour-only.

### 5.2 Tenant Repairs list (`RepairsPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Tenant maintenance tickets list. Blocks: (1) filter pill row — "All / Open / In progress / Resolved" using `.pill` + `.pill-active` (navy fill); (2) scrollable list of ticket cards — title, 1-line description, status badge, priority, created-at. No FAB. Primary CTA: sticky bottom button **"Report a new issue"** that pushes to triage chat (navy primary button, 44pt, full-width with 16px padding). States: empty ("No repairs yet" with friendly copy + primary CTA centred), loading (3 skeleton cards), error (inline retry). Accessibility: status colour paired with an icon; filter pills announce selected state; bottom CTA clears safe-area.

### 5.3 Tenant Ticket chat (`TicketChatPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Live chat on a maintenance ticket. Blocks: (1) header — frosted iOS or navy MD3, back button, title "Leaking tap – Kitchen", connection dot (green=connected, amber=reconnecting); (2) message stream — user bubble (navy fill, white text, 18/18/4/18 radius, right-aligned), other bubble (white, gray-200 border, 18/18/18/4, left-aligned, sender name + role above), date separators centred, typing indicator (3 bouncing navy dots); (3) composer at bottom — rounded input, camera icon, send icon (navy when enabled). Primary action: send. States: loading history (top skeleton), empty chat ("Start the conversation"), disconnected banner. Accessibility: send button labelled, composer grows to 4 lines.

### 5.4 Tenant Lease (`LeasePage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Read-only signed lease summary. Blocks: (1) hero card with green "Signed" badge, property address, lease dates, monthly rent in ZAR (tabular-nums); (2) section-card **"Parties"** — landlord + tenant rows with initials avatars; (3) section-card **"Terms"** — start/end, deposit, escalation %, payment day — label-upper on left, value navy right-aligned; (4) **"Documents"** row — signed PDF chip with download icon, signed date. Primary action: "View full PDF" primary button at bottom. States: loading (skeleton cards), no-lease ("No active lease" empty state with faint icon), pending-signing (amber banner "Signature required" linking to /signing). Accessibility: PDF button has role + aria-label.

### 5.5 Tenant Settings (`SettingsPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Tenant profile + preferences. Blocks: (1) profile card — 64px avatar, name, email, edit icon; (2) section "Account" — list rows: Change password, Notifications, Language; (3) section "Property" — list rows: My lease, My property, Report bug; (4) section "Legal" — Privacy, Terms, POPIA consent; (5) destructive row "Log out" in danger-600; (6) version footer in text-muted 12px. Use iOS hairline separators (0.5px rgba(0,0,0,.1)) OR MD3 list rows with 56dp minimum. Primary action: log out (with confirm dialog). States: loading profile, saving (disabled + spinner). Accessibility: rows are buttons with aria-label, destructive row announces "destructive".

### 5.6 Agent Dashboard (`DashboardPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Agent home. Blocks: (1) greeting — "Good afternoon, Michael" in navy large-title (iOS) or on navy MD3 bar (Android); (2) **KPI grid 2×2** — four cards: Properties, Active leases, Upcoming viewings, Pending signatures; each card: label-upper gray-500, `.stat-value` 24/700 navy tabular-nums, delta chip (green/red); (3) **"Today"** section-header then agenda list — 3 upcoming viewings with time, prospect, property; (4) **"Needs attention"** — leases awaiting signature. Primary action: tap KPI → drilldown. States: pull-to-refresh spinner at top, loading skeletons in each card, empty-day state. Accessibility: numbers announced with units ("12 properties").

### 5.7 Agent Properties list (`PropertiesPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Searchable property list. Blocks: (1) sticky search field — rounded 10px outlined input, leading magnifier icon, placeholder "Search by address or reference"; (2) optional filter chip row (All / Vacant / Occupied / Mixed); (3) property cards — 80×80px thumbnail left, title (suburb, city), address line, unit-count + occupancy chip (e.g., "3/4 occupied" green), chevron right; dividers or 12px gaps. No FAB on this list (showFab:false). Primary action: tap card → Property detail. States: empty ("No properties yet" + "+ Add property" primary), loading (6 skeleton cards), search no-results. Accessibility: search field focus ring navy, cards are full-width buttons.

### 5.8 Agent Viewing Calendar (`ViewingCalendarPage.vue`)

> Mobile, iOS + Android, **Klikk brand system**. Month grid of property viewings. Blocks: (1) month nav header — `<` Month Year `>` centred, 17/600 navy; (2) day-of-week labels (Mon..Sun, 11px label-upper gray-500); (3) 6-row calendar grid — today circled in navy, days with viewings show 1–3 stacked dots (navy / accent-pink / amber) below the date; (4) bottom sheet / expanded list for the selected day — viewing rows: time, property, prospect name, status badge. **Android shows a secondary-accent FAB** bottom-right (56dp, `+` icon, offset 18/88) to book a viewing; **iOS hides the FAB** and relies on a right-header `+` button instead. States: loading (inline overlay on grid), empty day ("No viewings"), offline banner. Accessibility: dates are buttons, selected state announced.

---

## 6. Reference screenshots to capture

Capture before running any Stitch generation. 12–16 shots total. Simulator builds preferred because Capacitor applies `platform-ios` / `platform-android` body classes that trigger the HIG vs MD3 CSS forks.

**Build commands** (do not run now; listed so the user knows how):
- Tenant iOS: `cd tenant-app && quasar dev -m capacitor -T ios` then press Cmd+S in Xcode simulator.
- Tenant Android: `cd tenant-app && quasar dev -m capacitor -T android` then Ctrl+S in Android Studio emulator.
- Agent: same commands in `agent-app/`.
- Fast alternative (browser-only, no platform class): `quasar dev` → Chrome at `http://localhost:9000/`, then toggle `document.body.classList.add('platform-ios')` in devtools.

**Shot list** (absolute paths are the source `.vue` for reference):

Tenant (6):
1. `tenant-app/src/pages/HomePage.vue` — iOS, with a pending-signature card visible
2. `tenant-app/src/pages/HomePage.vue` — Android, empty state (no repairs, no pending)
3. `tenant-app/src/pages/RepairsPage.vue` — iOS, "Open" filter active, 3+ tickets
4. `tenant-app/src/pages/TicketChatPage.vue` — iOS, mix of user + other bubbles + typing indicator
5. `tenant-app/src/pages/LeasePage.vue` — Android, signed lease present
6. `tenant-app/src/pages/SettingsPage.vue` — iOS, hairline separators visible

Agent (7):
7. `agent-app/src/pages/DashboardPage.vue` — iOS, KPI grid populated
8. `agent-app/src/pages/PropertiesPage.vue` — iOS, search empty + list populated
9. `agent-app/src/pages/PropertyDetailPage.vue` — Android (FAB visible), Units tab active
10. `agent-app/src/pages/LeasesPage.vue` — iOS, status chip "Active" selected
11. `agent-app/src/pages/ViewingCalendarPage.vue` — Android (FAB visible), month with dots
12. `agent-app/src/pages/ViewingDetailPage.vue` — iOS, status banner green
13. `agent-app/src/pages/BookViewingPage.vue` — iOS, step 1 of 2

Shared chrome (3):
14. `tenant-app/src/pages/LoginPage.vue` — iOS, navy hero + white form sheet
15. Tab bar close-up — iOS frosted (both apps look nearly identical)
16. Tab bar close-up — Android MD3 pill indicator (agent app, "Dashboard" active)

Feed shots 1, 7, 11 to Stitch first in Experimental Mode as **visual brand reference** when generating DESIGN.md; the rest are for per-screen fidelity prompts.

---

## 7. Suggested workflow

Step-by-step, low-risk, iterative:

1. **Create two Stitch projects**: "Klikk Tenant (Mobile)" and "Klikk Agent (Mobile)". Do not share a project — Stitch's DESIGN.md is per-project, and tab-bar contents differ enough that cross-contamination hurts.
2. **Seed DESIGN.md** in each project. Easiest path: upload screenshot 1 (tenant) or 7 (agent) plus the navy + accent logo, let Stitch extract DESIGN.md, then paste the *Brand paragraph* (§3) and *Component inventory paragraph* (§4) into the markdown editor and save. Verify the hexes landed — Stitch sometimes rounds colours.
3. **Generate Screen 1 (Home / Dashboard)** using §5.1 or §5.6. Pick *Mobile*, paste prompt, generate. Expect two or three variants; pick the one closest to the reference screenshot (shots 1 / 7).
4. **Refine with screenshot**. In Experimental Mode, attach the corresponding reference screenshot and add a one-line refinement ("match the status-badge style in the reference exactly"). Iterate once or twice.
5. **Chain next screen**. Use Stitch's "generate next screen" to go Home → Repairs list → Ticket chat (tenant) and Dashboard → Properties → Property detail → Calendar (agent). Stitch keeps DESIGN.md consistent across the chain.
6. **Export to Figma** once you have a screen you like. Open the Stitch→Figma plugin, paste. Work in Figma for any typography/spacing nudges Stitch got wrong.
7. **Generate the remaining 6 screens** (§5.2–§5.8 minus the two already done). Keep each prompt < 120 words; do not restate the brand — DESIGN.md carries it.
8. **Run two platform passes per screen**: first prompt "iOS variant using Apple HIG conventions", regenerate with "Android variant using Material Design 3 with navy MD3 top bar and white MD3 bottom nav". Save both in the same Stitch frame.
9. **Assemble a review board** in Figma: 2 columns (iOS / Android) × 8 rows (screens) for stakeholder sign-off.
10. **Hand back** the Figma file + the final DESIGN.md to the dev team; do NOT take Stitch's HTML/CSS straight — our Quasar components already implement the tokens.

---

## 8. Risks / what Stitch probably won't handle

- **Role-based party colours on PropertyDetailPage and the lease document** (`--party-landlord-base`, `--party-tenant-base`, etc. in `admin/src/assets/main.css` L41–55). These are *semantic* (landlord/tenant/occupant/witness), not brand chrome. Stitch will almost certainly collapse them to generic colour chips. Flag: exclude from the Stitch scope and keep the existing DocumentPage implementation.
- **TipTap lease editor** (`klikk-leases-tiptap-editor`). A rich-text editor with merge-field placeholders, bubble menu, table grid, and custom marks. Stitch generates static UIs — it cannot model TipTap's schema or the bubble-menu interaction. Do not prompt for it.
- **Native e-signing flow** (`signed_pdf_file`, `signer_role` links, Gotenberg-rendered signature page). Visual surface for `LeaseSigningPage.vue` can be redesigned in Stitch, but the signature-placement canvas and role-based signer sequencing are backend-driven; don't let Stitch invent a "signature widget" that doesn't exist.
- **Pull-to-refresh + native gestures.** Stitch renders static frames. It will draw a spinner but won't convey the gesture. Document in the spec, don't expect fidelity.
- **Android FAB vs iOS no-FAB split.** Stitch does not have an explicit platform toggle. The only way to enforce the split is to write the platform rule into every relevant prompt (done in §5.6 and §5.8) and to keep DESIGN.md's *Components paragraph* explicit about it. Expect 1–2 regeneration cycles where Stitch still puts a FAB on iOS — correct with a follow-up instruction.
- **Capacitor safe-area insets** (`env(safe-area-inset-bottom)`). Stitch will draw a generic home-indicator but will not respect our padding tokens. Visual only — no functional risk.
- **Exact Inter optical sizes.** Stitch will substitute its default Inter or fallback; radii and weights usually land correctly, but verify the 11px Caption-2 label on the tab bar — Stitch tends to bump this to 12px.
- **DocumentPage PDF chrome** (`--doc-header-text`, `--doc-canvas-bg` etc.). This is a legal-document viewer, not an app screen. Out of scope for Stitch; keep in Vue.
- **Data-density.** Our real tables (LeasesPage, PropertyDetailPage) carry 6–10 columns of info. Stitch prefers airy layouts and may silently drop columns. Always prompt with the explicit block list and check the output for missing fields.

---

Sources:
- [From Google Stitch to Figma — html.to.design](https://html.to.design/blog/from-google-stitch-to-figma/)
- [Design Mobile App UI with Google Stitch — Codecademy](https://www.codecademy.com/article/google-stitch-tutorial-ai-powered-ui-design-tool)
- [What Is Google Stitch? — MindStudio](https://www.mindstudio.ai/blog/what-is-google-stitch-ai-native-design-canvas)
- [Google Stitch Complete Guide 2026 — NxCode](https://www.nxcode.io/resources/news/google-stitch-complete-guide-vibe-design-2026)
- [What Is Google Stitch's Design.md File? — MindStudio](https://www.mindstudio.ai/blog/what-is-google-stitch-design-md-file)
- [DESIGN.md: Google Stitch's AI Brand Consistency Feature — YouMind](https://youmind.com/blog/google-stitch-design-md-ai-brand-consistency)
- [What The Hell Is Google Stitch's DESIGN.md — DesignWhine](https://www.designwhine.com/what-the-hell-is-google-stitchs-design-md/)
- [Exporting Stitch to Figma — Google AI Developers Forum](https://discuss.ai.google.dev/t/exporting-stitch-to-figma/104903)
- [Design UI using AI with Stitch — Google blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/)

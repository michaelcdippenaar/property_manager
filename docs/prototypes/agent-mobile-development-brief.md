# Klikk Agent Mobile — Development Brief

_Feeding the dev agent. The site-tool companion to the agent web app._

**Source prototype:**
- `docs/prototypes/agent-mobile.html` — 12 frames across 4 sections
- `docs/prototypes/agent-mobile.png` — retina capture, 2.3 MB
- PNG copy for web hosting: `website/public/prototypes/agent-mobile.png`

**Sister briefs:**
- `docs/prototypes/agent-app-development-brief.md` — agent **web** (the dashboard)
- `docs/prototypes/tenant-app-development-brief.md` — the tenant mobile app (same stack, different user)

---

## 1. Identity (this is the whole brief in one line)

**"I'm at a property."**

The agent mobile app is a **site tool**, not a dashboard. You open it because your body is somewhere — outside a unit for a viewing, inside for an inspection, on a driveway watching a contractor finish a job. The app knows where you are (GPS + calendar) and opens to the thing you're there to do.

If a feature isn't something the agent does **standing up at a property**, it does not belong in this app. It belongs in the web app.

### What that means concretely

- **Context-aware home**: the app picks the right property for you; you don't pick it.
- **Camera-first**: every flow ends with photos. The camera button is as important as the nav.
- **Offline-first**: old buildings, basements, weak rural signal. The app works, then syncs later.
- **Big tap-targets**: 48 pt minimum. You might be holding a clipboard, wearing gloves, standing in rain.
- **Short sessions**: 5–30 min of use, then driving, then 5 min more. Resumption must be zero-friction.
- **Signature capable**: the tenant signs on your phone at move-in/out — that's the whole differentiator vs paper.
- **Voice notes**: typing while walking a unit is bad. Tap mic, speak, move on.

### What it deliberately does NOT do

No portfolio KPIs. No task list across 100 properties. No property grid with filters. No bulk operations. No trust-account work. No lease drafting. No marketing / listing management. No messenger tab (quick-replies on notifications only — use the OS).

**If the agent is sitting at a desk, the web app is where they should be.**

---

## 2. The 4-tab IA

| Index | Tab | Icon (Lucide) | Purpose |
|---|---|---|---|
| 0 | **Now** | `home` | The property you're at (or about to be at) |
| 1 | **Inspect** | `clipboard` | Room-by-room inspection flow |
| 2 | **Sign** | `pen` | Viewings, FICA capture, lease send |
| 3 | **Log** | `list` | Your visit history (proof + reference) |

Same elevated-active pattern as the tenant app: **36 × 36 navy circle + 54 × 54 pink radial-gradient cushion**, icon translated up 10 px so it breaks the bottom line. This is the only elevated element in the whole UI.

The tab bar disappears during active flows (inspection in progress, camera open, signature capture) and is replaced by a full-width **bottom-action bar** with a single primary button. This is deliberate — during a flow the agent has one next step, not four tabs of options.

### Why not "Emergency" as a 5th tab?

Emergency is accessed from:
1. A push notification ("tenant called for X") → deep-link into the dispatch sheet
2. A quick-tile on the Now home screen

Making it a tab would train the agent to look for emergencies. The product's job is the opposite — emergencies come to the agent, they don't go hunting.

---

## 3. Design foundations

### 3.1 Colour tokens (identical to tenant/agent web apps)

| Token | Value | Use in site tool |
|---|---|---|
| `navy` | `#2B2D6E` | Active tab, primary CTAs, property card title, map supplier pin |
| `accent` | `#FF3D7F` | Event banner (scheduled event), map home pin, quick-tile accent |
| `success-600` | `#0d9488` | Completed inspection, "synced" chip, check boxes |
| `warning-600` | `#d97706` | "Arriving" badge, defect severity, offline warning |
| `danger-600` | `#dc2626` | Emergency hero, "offline" chip, urgent defect, red dispatch CTA |
| `surface` | `#F5F5F8` | App background |
| `surface-secondary` | `#F0EFF8` | Sys-cards, progress rail bg, quick-tile icon bg |

### 3.2 Typography

Prototype uses **Fraunces** (display, serif) + **DM Sans** (body). In production, match the admin spec — **Inter** at 15 px base. Keep the prototype's hierarchy:

- Property card title: 17 px · weight 500 · serif feel → in Inter use weight 600 + letter-spacing −0.01em
- Section `grp-lbl`: 10 px · weight 700 · uppercase · letter-spacing 0.1em · navy
- Agenda title: 12 px · weight 600
- Agenda sub / meta: 10–11 px · gray-500
- **Floor**: 10 px on sub-meta only. 9 px is reserved for tag-in-badge contexts, not body copy.

### 3.3 Icons, shadows, radii

- **Lucide only**, stroke-width 1.75 at 14–18 px, 1.5 at 22–32 px
- Shadows: same three-tier system (`soft` / `lifted` / `floating`) as tenant app
- Radii: 10 px chips · 12 px cards · 14 px sheets · 999 px pills

### 3.4 Phone spec

320 × 658 in the prototype = iPhone 13 proportions with home indicator removed. Build for **375 pt** as baseline, scale cleanly to **428 pt**. Status bar 44 pt. Tab bar 78 pt. Bottom-action bar (when active) 72 pt.

---

## 4. Cross-cutting systems

### 4.1 Ambient context strip

Between the app header and the main content, a **7-pt high strip** shows where the app thinks you are: `You're at Office · 15 Dorp St` or `Arriving at 7 Dorp St · 2 min away`. This is the "I know where you are" feedback loop — the agent should trust the app's guess before they trust the screen below it.

Driven by GPS + the day's calendar:
- If within 200 m of a scheduled-visit property → "Arriving at …"
- If at a property with an active event → "You're at …"
- If stationary elsewhere (office, home, lunch) → "You're at Office" (or the reverse-geocoded locality)

### 4.2 Offline indicator

Top-right of the app header, a small chip:
- **Synced** (green-ish, `cloud` icon) — default state
- **Offline** (danger-tinted, `wifi-off` icon) — no connection
- **Syncing** (amber, with spinner) — catching up after reconnect

Every screen that can be used offline shows a sys-card reinforcing the behaviour: *"No signal — photos & notes save locally, sync when back online."* Agents need to trust the app doesn't lose their work.

### 4.3 Property card

The app's centre of gravity. Used on Now home, Sign prospect flow, Log detail. Anatomy:
- **Image band** (88 px, gradient placeholder until real photos exist)
- **Eyebrow** (10 px uppercase, navy) — context like "Today · move-out" or "Viewing · 14:00"
- **Title** (serif/editorial, 17 px, gray-900) — street address + unit
- **Sub line** (11 px, gray-500) — suburb · tenant · rent, dot-separated

### 4.4 Event banner (the pink strip)

When there's an active or imminent event on the current property, a pink gradient banner sits below the property card with: label · title · meta · big white CTA. Three tones:
- **Accent pink** — scheduled event approaching ("Starts in 12 min")
- **Amber** — event requires attention ("Supplier arriving")
- **Navy** — ready-to-start neutral ("Begin · 6 rooms")

The CTA inside the banner is always a **white button with navy text** — it inverts from the screen's palette so the agent's eye snaps to it.

### 4.5 Progress rail

On multi-step flows (inspection, FICA, viewing checklist), a thin rail sits below the sheet header showing: `Step N of M · <current step name>` + right-aligned live counter (e.g. "1 defect") + a progress-bar track. Accent pink fill once progress is irreversible, navy during reversible setup steps.

### 4.6 Big-button system

All primary actions use `.btn-big` — 48 pt tall, 14 px font weight 700, large icon. Three variants:
- `.btn-big.primary` (navy bg) — "Next", "Close & send", "Back to Now"
- `.btn-big.accent` (pink bg) — used sparingly, only for scheduled-event CTAs
- `.btn-big.outline` (white + border) — secondary
- `.btn-big.danger` (red bg) — emergency dispatch confirmation only

Two-button rows pair outline + primary, never two primaries.

### 4.7 Sys-cards in context

Used inline in flows (not in threads like tenant app). Announce:
- What Klikk AI did ("pre-filled from FICA scan · tenant's legal name matches ID")
- What will happen next ("PDF will be emailed to Sarah, Sarah (agent), landlord")
- Warning state ("No signal · photos save locally")

Short, icon-led, no action button inside the card.

---

## 5. Tab 1 — Now · 3 frames

The home state. Context-aware. One property at a time, never a grid.

### Frame 1 — Quiet morning
Agent at the office, no visit yet. Home shows:
1. Ambient strip: "You're at Office · 15 Dorp St"
2. **Empty-state block**: `map-pin` icon, "Not at a property yet", "Your day starts at 11:00 — here's what's on the list"
3. `Today · 3 visits` group with 3 agenda rows (each: time · coloured dot · title · property-tenant line)
4. `Quick actions` two-up tile grid: **Emergency** (accent pink icon) + **Unplanned inspection**

The empty-state is deliberate. Most apps would show today's agenda at the top. Here, the top is the *identity question* ("are you at a property?") and the answer is currently "no". Agenda sits below as secondary.

### Frame 2 — Event approaching
GPS detects you're 2 min from 7 Dorp St, which has an 11:00 move-out in the calendar. The app flips:
1. Ambient: "Arriving at 7 Dorp St · 2 min away"
2. **Property card** for 7 Dorp St auto-loaded
3. **Pink event banner**: "Move-out inspection · Starts in 12 min · Sarah is on her way" + CTA "Start inspection now"
4. Two-button row: "Call Sarah" + "Directions"
5. `Recent on this property` strip — last 3 relevant events (rent paid, geyser replaced, lease ends in 13 days)

The agent didn't ask for any of this — the app inferred it.

### Frame 3 — Offline at property
Agent is inside the unit, signal is dead:
1. Offline chip (danger-tinted) in header
2. Property card with "On site · GPS confirmed" eyebrow
3. Sys-card warning: "No signal — photos & notes save locally"
4. **Navy event banner** (ready state): "Begin — 6 rooms"
5. `Pre-check` checklist (phone charged ✓, template loaded ✓, confirm tenant present, record meters first)

The navy banner (vs pink in Frame 2) signals: you're past "approaching" and into "ready to work".

---

## 6. Tab 2 — Inspect · 3 frames

The room-by-room inspection flow. Replaces paper clipboards and WhatsApp photo dumps.

### Frame 4 — Pre-inspection
Sheet header (back button + title). Progress rail: "Step 1 of 8 · Pre-check · 0 defects · 12%".
1. `Who's present` card — tenant avatar + name + "confirmed present" check
2. `Meter readings` — two rows (Electricity, Water), each with an inline "Capture" button that opens the camera. **Photo is mandatory** — you can't progress without one.
3. Bottom-action bar: "Next · start with kitchen"

Meter readings go first because they're the hardest to recover if forgotten. The app enforces order.

### Frame 5 — Kitchen in progress
Progress rail now at 38%, "1 defect" in warning amber.
1. **Room chips** (horizontal scroll): Entrance ✓ · **Kitchen** (active) · Living · Bedroom 1 · Bathroom. Done rooms go green, active room navy, future rooms neutral.
2. `Photos · 3` with a **3-column grid**. Each tile has a caption tag ("Wide", "Cupboards", "Stove"). The defect photo has a red dot indicator.
3. "Add photo" full-width outline button
4. `Defects · 1` section with a defect card: thumb + title + severity badge ("Repair" amber) + cost estimate
5. "Log another defect" full-width outline button
6. Bottom-action row: "Back" + "Next room"

Key insight: **defects are a photo with context**, not a text field. You always take the photo first, then annotate.

### Frame 6 — Summary + tenant signature
Progress rail at 100% "Step 8 of 8 · Sign-off · 3 defects".
1. **Stats card** — 3 columns: 6 Rooms · 18 Photos · 3 Defects (serif numbers, 20 px)
2. `Deductions · R1,890` — itemised lines (stove R350, repaint R1,200, blind R340)
3. `Tenant signature · Sarah v.d. Merwe` label
4. **Signature pad** (dashed border, 140 px tall) — agent hands phone to tenant, they sign with finger. Signed signature renders inline (the SVG path in the prototype is a placeholder).
5. Sys-card (success green): "PDF will be emailed to Sarah, Sarah (agent), landlord"
6. Bottom-action bar: "Close inspection & send"

Closing fires: PDF generation (Gotenberg), email distribution, timeline entry on the property, state transition from stage 8 → 9 (Repairs & Cleaning) in the web app's lifecycle.

---

## 7. Tab 3 — Sign · 3 frames

Viewings, FICA, lease send. The pre-tenancy half of the lifecycle on mobile.

### Frame 7 — Viewing · prospect
Ambient: "You're at 56 Andringa St". Property card with "Viewing · 14:00" eyebrow.
1. `Prospect` card — avatar + "Nomsa Mthembu" + "Registered interest 3 days ago · via Property24" + two tags: **Pre-screened** (green) + **3× rule** (navy — she earns 3× rent). One-tap call button on the right.
2. `On-site checklist · 1/4`:
   - ✓ Unit unlocked & aired
   - [ ] Walk the unit · highlight geyser, parking
   - [ ] Capture ID for FICA (if applying)
   - [ ] Send lease link before they leave

The last item is the conversion goal. The app gently pushes "before they leave" — the whole point is to not let a hot prospect walk out without a lease.

### Frame 8 — FICA · ID capture
Full-screen camera view (dark background, status bar white):
1. Sheet header "FICA · step 1 of 2 · Scan ID document"
2. **Camera frame** (4:3, dark) with: corner markers, dashed inner guide, placeholder ID silhouette, hint text "Align ID within the frame"
3. `Auto-extracted` section below the camera (only appears after capture):
   - ID number: `880514 2745 083`
   - Full name: `Nomsa P. Mthembu`
   - DOB: `14 May 1988`
4. POPIA footnote: "ID stored encrypted · auto-deleted if not leased within 30 days"
5. **Shutter button** (56 px, white with navy ring) bottom-centre, flanked by rotate and flash icons

OCR runs on-device (ML Kit on Android, Vision on iOS) first, falls back to server OCR if the client result has low confidence. The extracted fields are **editable** — OCR isn't infallible and the agent is the source of truth.

### Frame 9 — Lease sent · confirmation
Success state after tapping "Send lease":
1. **Green celebration card** (gradient success-50 → white) with big check, "Lease sent to Nomsa", "WhatsApp delivered · e-sign link valid 48h"
2. `Lease summary` card — property, rent (R 11,000/mo), deposit (R 22,000), start (1 May 2026 · 12 months), template (Stellenbosch Std · RHA v3)
3. Sys-card: "Klikk AI pre-filled from FICA scan · tenant's legal name matches ID"
4. `Track status` agenda:
   - Now · Lease delivered · "Via WhatsApp · also email backup"
   - Next · Awaiting Nomsa's signature · "You'll get a push when she signs"
5. Bottom-action: "Done · back to Now"

Delivery is **WhatsApp-first** because that's how SA rental actually works. Email is the audit backup.

---

## 8. Tab 4 — Log · 1 frame (plus emergency flow · 2 frames)

### Frame 10 — Visit log
Your proof-of-visit history. Every log entry is GPS-stamped, photo-attached, timestamp-proven.

Header: "Your week · 12 visits · 38 photos · 4 signed docs" ambient strip.

Grouped by day:
- **Today**: Move-out inspection · 7 Dorp St · Signed · 45 min · 18 photos · Viewing · Nomsa · Lease sent · 22 min · FICA done · Supplier sign-off · John · Approved R4,700 · 3 line items
- **Yesterday**: Periodic inspection · 44 Church St · Signed · No defects

Each row: 44 × 44 thumb · title · property + status badge · time range + metadata. Tap → detail view with full photo set + signed PDF + timeline (not shown in prototype — it's a reuse of existing admin views).

**Commercial value**: this is the owner/landlord's audit trail. When there's a dispute, the agent opens the log, filters to the property, and the evidence is all there. Paper clipboards can't do this.

### Frame 11 — Emergency dispatch sheet
Not reached via the Log tab. Reached via a push notification ("tenant called emergency") or the "Emergency" quick-tile on Now home.

Red gradient hero:
- Pulsing white dot + "URGENT · Geyser leak" label
- Title: "12 Dorp St, Unit 1"
- Sub: "Michael D. · tenant called · water in ceiling · isolator off"

Below: **approved plumbers sorted by ETA**. Each row:
- Avatar + name · company
- ETA + star rating + job count
- Badges: "Approved by owner" (green) · specialty · call-out fee if any

The **best pick** is surfaced with a green border and a "Best pick" corner badge — based on: owner-approved AND lowest ETA AND no call-out fee. One tap on the send button opens the confirmation.

Below the list: "Call Michael first" outline button (the agent might want to triage before dispatching).

Bottom-action: **red "Dispatch John · notify tenant"** button. This is the only place in the app where `btn-big.danger` is used.

### Frame 12 — Dispatched confirmation
After dispatch:
1. Green celebration card: "Dispatch sent · John accepted · tenant notified · ticket KL-0489 opened"
2. **Live ETA map** (mini map, 120 px tall) with supplier pin (navy), home pin (pink), diagonal track line, ETA chip "22 min · 8.4 km"
3. `Thread updates · auto` — sys-cards showing what's happened:
   - Klikk AI messaged Michael (acknowledgement + instructions)
   - John confirmed · R0 call-out (approved contract)
   - Owner auto-notified · geyser under warranty (expires 12 Jun)
4. Call John outline button
5. Bottom-action: "Back to Now"

The emergency flow is the product's **most visible AI value**. Klikk AI:
- Picked the best supplier
- Messaged the tenant with ETA and instructions
- Checked warranty status
- Notified the owner

The agent pressed one button. This is the wedge that beats Payprop's "email the landlord, email the plumber, wait for replies" status quo.

---

## 9. Build order

### Phase 0 — Foundations (1 week)

1. Match the tenant app's token system, Lucide icons, shadows, phone spec.
2. **Offline-first infrastructure**: SQLite local store, background sync queue, optimistic UI, conflict resolution (last-write-wins is fine for inspection data). Use `drift` / `floor` in Flutter, or Realm.
3. **GPS + calendar context engine**: background location (low-power), read today's calendar, compute "which property am I near?". This drives the Now tab.
4. **Camera wrapper**: photos must be compressed (1600 px long edge, JPEG q80), EXIF-stripped but GPS-and-timestamp-retained in sidecar metadata. Store in local queue until synced.
5. Build the 4-tab shell with elevated-active + bottom-action bar replacement pattern.
6. `PropertyCard`, `EventBanner`, `AmbientStrip`, `OfflineChip`, `ProgressRail`, `BigButton`, `SysCard` as Flutter widgets.

### Phase 1 — Inspect flow (2–3 weeks)

The highest-value flow, and the hardest to get right.

1. `InspectionTemplate` data model — rooms, required photos per room, meter types, common defects.
2. `InspectionSession` — local-only draft, synced on close. Contains all photos + notes + signatures.
3. Screens:
   - `InspectPreCheckScreen` — presence + meters
   - `InspectRoomScreen` — reusable for all rooms, parameterised
   - `DefectDialog` — photo + title + severity + cost estimate
   - `InspectSummaryScreen` — stats + deductions + signature pad
4. `SignaturePad` widget (use `signature` package in Flutter, capture as SVG path → PNG export).
5. **PDF generation**: trigger Gotenberg on sync close, receive signed PDF URL, attach to session. The `klikk-platform-gotenberg` and `klikk-leases-pdf-export` skills cover the pipeline.
6. Email distribution via backend: tenant, agent, landlord.
7. State transition: close inspection at stage 8 → move property to stage 9 in web app's lifecycle.

### Phase 2 — Sign flow (2 weeks)

1. `ViewingChecklist` — customisable per-agency.
2. `FICACaptureScreen` — camera + on-device OCR (ML Kit for Android, Vision for iOS) + editable field confirmation.
3. POPIA flow — consent capture before scan, 30-day auto-deletion if lease doesn't execute.
4. `LeaseSendScreen` — pre-fills from FICA data, selects template, generates e-sign link via existing backend, sends via WhatsApp Business API + email.
5. Push notification wiring for "Nomsa signed" → deep-link back into the log entry.

### Phase 3 — Now + Log (1 week)

Mostly thin views over data the web app already exposes.

1. `NowScreen` — queries context engine, renders empty/approaching/on-site states.
2. `VisitLogScreen` — paginated list of completed sessions (inspections, viewings, supplier sign-offs). Grouped by date.
3. Visit detail view — reuse the admin web views in a mobile layout.

### Phase 4 — Emergency dispatch (2 weeks)

1. Push notification handling — deep-link from a "tenant emergency" notification into the dispatch sheet, pre-filled with tenant + issue.
2. `SupplierPicker` — backend endpoint returns approved suppliers ordered by ETA (uses supplier current location if they're on-shift, or last-known), with AI "best pick" flag.
3. `DispatchConfirm` flow — send, open ticket in tenant's Problems thread, notify owner.
4. Live ETA subscription — supplier app publishes location, agent app subscribes via websocket or pub/sub.

### Phase 5 — Supplier sign-off (1 week)

Not shown in the prototype but implied in Log/Now agendas. A variant of the inspection flow: walk the unit with the contractor, accept or reject their line items, approve payment, log warranty.

---

## 10. Data contracts

```ts
type VisitType = 'move_in_inspection' | 'move_out_inspection' | 'periodic_inspection' |
                 'viewing' | 'supplier_signoff' | 'emergency_dispatch';

type InspectionSession = {
  id: string;
  propertyId: number;
  tenantId: string;
  agentId: string;
  type: 'move_in' | 'move_out' | 'periodic';
  startedAt: string;       // ISO
  completedAt?: string;
  gpsConfirmedAt?: string; // ISO when GPS matched property location
  rooms: Array<{
    name: string;          // "Kitchen", "Bedroom 1"
    photos: Array<{ id: string; caption?: string; localPath?: string; remoteUrl?: string }>;
    defects: Array<{
      id: string;
      title: string;
      photoIds: string[];
      severity: 'repair' | 'replace' | 'note';
      estimateZar?: number;
      note?: string;
    }>;
  }>;
  meterReadings?: {
    electricity?: { value: number; photoId: string };
    water?: { value: number; photoId: string };
  };
  tenantSignatureSvg?: string;
  tenantSignedAt?: string;
  deductionsZar: number;
  pdfUrl?: string;         // Gotenberg result, null until synced
  syncState: 'local' | 'syncing' | 'synced' | 'error';
};

type ProspectViewing = {
  id: string;
  propertyId: number;
  prospect: { id: string; name: string; phone: string; email?: string };
  startedAt: string;
  completedAt?: string;
  checklist: Array<{ id: string; label: string; done: boolean; doneAt?: string }>;
  ficaCapture?: {
    idNumber: string;
    fullName: string;
    dob: string;
    idPhotoLocalPath?: string;
    idPhotoRemoteUrl?: string;
    ocrConfidence: number;
    capturedAt: string;
  };
  leaseSentAt?: string;
  leaseSignedAt?: string;
};

type EmergencyDispatch = {
  id: string;
  propertyId: number;
  reportedBy: 'tenant' | 'owner' | 'agent';
  summary: string;          // "Geyser leak · water in ceiling"
  severity: 'urgent' | 'high' | 'normal';
  createdAt: string;
  approvedSuppliers: Array<{
    id: string;
    name: string;
    company: string;
    etaMinutes: number;
    rating: number;
    jobCount: number;
    approvedByOwner: boolean;
    specialties: string[];
    callOutFeeZar: number;
    bestPick: boolean;
  }>;
  dispatchedSupplierId?: string;
  dispatchedAt?: string;
  ticketId?: string;        // Tenant app ticket
};
```

---

## 11. Flutter stack (specific recommendations)

- **State**: Riverpod 2 for app-wide state; per-flow state in `StateNotifier`s.
- **Storage**: Drift (SQLite) for local-first data; flutter_secure_storage for auth + FICA fields.
- **Camera**: `camera` package for raw capture; `image` for compression.
- **OCR**: `google_mlkit_text_recognition` for on-device.
- **Signature**: `signature` package.
- **Maps**: `flutter_map` + OpenStreetMap tiles (avoid Google Maps cost at scale).
- **Push**: Firebase Cloud Messaging + local-notifications package for deep-links.
- **WhatsApp send**: backend-only (WhatsApp Business API); app just triggers the backend.
- **PDF preview**: `pdfx` or native webview.

---

## 12. Anti-patterns

- **Do not** add a 5th tab. Four tabs is the IA. "Settings" lives behind a long-press on the role pill.
- **Do not** hide the offline chip when online — it tells the agent "sync is OK" even when they're not worried about it. It's ambient confidence.
- **Do not** use the accent pink for anything other than scheduled-event CTAs and the home map pin. Overuse dilutes the "your tenant is there" signal.
- **Do not** let the inspection flow be resumable from anywhere but the Now tab. Resumption must be context-aware — if the agent has left the property, the session is paused and flagged.
- **Do not** build a tab-based inbox for tenant messages. Quick-reply from push notifications only. If the agent wants full messenger UX, open the tenant thread on the web.
- **Do not** copy the agent web app's Tasks layer into a mobile tab. Tasks are a desk activity.
- **Do not** ship without offline working. Offline is the bet. If offline fails, the app fails.

---

## 13. Success signals

1. **Inspection time drops from 60 min (paper) to < 40 min** including tenant signature and PDF delivery.
2. **Zero unsigned inspections** after week 4 — the signature pad + mandatory-before-close gating eliminates the "I'll get them to sign later" failure mode.
3. **Deposit dispute rate drops by > 50%** within 6 months. Photos + GPS + timestamps + signatures make the evidence unassailable.
4. **Emergency response time < 5 min** from tenant call to supplier dispatched. The 60-second sheet is the target.
5. **Lease-sent-at-viewing rate > 40%** of qualifying prospects. The FICA + "before they leave" flow converts on-site heat that cools by the time agents get back to the desk.
6. **Agents never reach for a paper clipboard** after 30 days of use. If they do, the camera UX is wrong.

---

## 14. References in this repo

| File | Purpose |
|---|---|
| `docs/prototypes/agent-mobile.html` | Interactive prototype · 12 frames |
| `docs/prototypes/agent-mobile.png` | Retina capture · 2.3 MB |
| `website/public/prototypes/agent-mobile.png` | Public copy for marketing use |
| `docs/prototypes/agent-app-development-brief.md` | **The web admin** — how the mobile hands off |
| `docs/prototypes/tenant-app-development-brief.md` | Tenant mobile · same stack, different user |
| `content/product/lifecycle.yaml` | 15-stage lifecycle authority · inspection fires state transitions |
| `.claude/skills/klikk-design-mobile-ux/` | iOS (HIG) + Android (MD3) platform-correct patterns |
| `.claude/skills/klikk-leases-pdf-export/` | HTML-to-PDF pipeline for inspection reports |
| `.claude/skills/klikk-platform-gotenberg/` | The PDF service |

---

## 15. The one-paragraph soul

An agent opens the app. Within 2 seconds the screen shows the property they're about to walk into, with a pink banner counting down to the event and a white button to start it. They tap start. 40 minutes later they hand their phone to the tenant, who signs with a finger. Another tap and a legally-compliant signed PDF lands in three inboxes. The agent drives to the next property. The app fades into the background — it was never the point. The point was getting out the door with the job done right.

**If this paragraph is true for the shipped app, we won. If it requires caveats, we didn't.**

---

_End of brief. When the flow evolves, update `agent-mobile.html` first, regenerate the PNG, then append here. Do not fork into parallel docs._

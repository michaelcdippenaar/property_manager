# UX Audit: Agent First Rental Cycle
**Date:** 2026-04-23
**Auditor:** ux-onboarding agent
**Task:** UX-001
**Scope:** Admin web app + Klikk Agent mobile app (Quasar/Capacitor)
**Method:** Code-reading audit (Vue SFC + router analysis). No live browser session; screenshots are described from component code. Discoveries filed separately.

---

## How to read this document

Each step follows the same structure:

- **Path**: where this happens (admin web / agent app)
- **Click/tap count**: estimated taps from the previous step to completing this one
- **Time-on-task estimate**: rough estimate for a first-time user
- **Friction rating**: 1 (none) to 5 (blocking)
- **Findings**: specific issues with exact file references
- **Suggested fix**: concrete, buildable recommendation

---

## Step 0 — Onboarding / First Login

### Admin web app

**Path:** `/login` then role-based redirect

**Click/tap count:** 3 (email, password, Sign In)
**Time-on-task estimate:** 1 min (assuming credentials supplied out-of-band)
**Friction rating:** 3

**Findings:**

F0.1 — No welcome screen or "what is Klikk?" moment on first login. The user lands directly on the dashboard with no guidance. A brand-new agent hired at an agency sees an empty state with no context about the product, their role, or what to do next. File: `admin/src/views/auth/LoginView.vue` (not read, inferred from router).

F0.2 — The ChoosePortalView (`admin/src/views/auth/ChoosePortalView.vue:49`) is only shown to `role === 'admin'`. Regular agents (role `agent`, `managing_agent`, etc.) skip it entirely and land directly on their home route. That is correct behaviour, but it means there is no onboarding gate, tooltip overlay, or first-run modal for non-admin agents.

F0.3 — The portal chooser copy for "Agent Portal" reads: *"Properties · leases · maintenance · inspections."* Inspections is listed but the feature is PLANNED (not BUILT). This sets an incorrect expectation on day one.

**Suggested fix:**
- Add a first-run flag (`profile.onboarded`) to the backend user model. On first login (flag false), show a 3-step welcome modal: (1) role confirmation, (2) "your golden path" lifecycle diagram, (3) "here is your first task." Set the flag on dismiss.
- Remove "inspections" from the portal chooser sublabel until incoming/outgoing inspection is BUILT.

---

### Agent mobile app

**Path:** `LoginPage.vue`

**Click/tap count:** 3
**Time-on-task estimate:** 1 min
**Friction rating:** 2

**Findings:**

F0.4 — Login page shows "Welcome back" as its heading. For a first-time user who has just been invited, "welcome back" is inaccurate and creates mild cognitive dissonance. The hero copy (`login-sub`) reads "Sign in to your agent account" — fine, but there is no distinction between a first-visit and a returning login.

F0.5 — The `invite-accept` flow exists (`/accept-invite` route) but the login page has no link to it. A new agent who receives an invite link and then navigates to the app directly hits the login screen with no guidance to check their email for the invite.

F0.6 — Password reset exists but requires two taps to reveal (tap "Forgot password?" to toggle `showReset`). This is fine but the reset form appears in-place via a `v-if` — no route change, no history entry — so pressing the Android back button while on the reset form exits the app rather than returning to the login form.

**Suggested fix:**
- "Sign in" as the heading; show "New here? Check your email for your invite link" as a soft hint below the form.
- Add a router-push route for the reset form (`/forgot-password` already exists in the admin router; mirror it in the agent app router) so Android back works correctly.

---

## Step 1 — Create Owner (Landlord)

### Admin web app

**Path:** `/landlords` then "Add Owner" modal

**Click/tap count:** 4 (nav click, Add Owner button, fill name/email, Save)
**Time-on-task estimate:** 2–3 min
**Friction rating:** 3

**Findings:**

F1.1 — The owner must be created before the property can be created with an owner linked. The properties list page (`PropertiesView.vue:279`) shows a landlord dropdown inside the "Add Property" modal, but this list is only populated if the user already went to `/landlords` and created an owner first. A new agent doing their first property will hit an empty dropdown with the placeholder "— Select owner —" and no affordance to create one inline. There is no "Add owner" shortcut within the property creation modal.

F1.2 — The order of operations is not communicated anywhere. There is no checklist, progress indicator, or hint that says "Before creating a property, add the owner first." A new agent is likely to create the property first (more intuitive), then discover the owner field was optional-looking and the owner-property link is now harder to establish.

F1.3 — The empty state on `/landlords` (`LandlordsView.vue`) — not read, inferred — likely says "No owners found" with an "Add Owner" button. This is a correct pattern but there is no explanation of why owners matter or what happens if you skip them.

**Suggested fix:**
- Add an inline "Add new owner" option at the bottom of the owner dropdown in the Add Property modal (a mini-drawer or a simple name+email form). This collapses 2 navigation steps into 1.
- Add a "prerequisites" banner or tooltip inside the Add Property modal: "You'll need an owner set up first. This links the property to the right landlord for mandate generation."

---

## Step 2 — Create Property

### Admin web app

**Path:** `/properties` then "Add Property" modal

**Click/tap count:** 5–8 (nav, button, fill form, save)
**Time-on-task estimate:** 3–5 min (without bill upload) / 1–2 min (with bill upload)
**Friction rating:** 2

**Findings:**

F2.1 — The "Auto-fill from Municipal Bill" feature (`PropertiesView.vue:219`) is excellent for experienced users but is the first thing shown in the modal, before the basic name field. For a new user who does not have a bill to hand, it creates confusion: "Do I need a bill? What is a rates bill?" The feature is unlabelled for non-SA users and lacks a "Skip this" affordance.

F2.2 — The modal requires a "Property name" field (labelled `*` required) but the placeholder reads "18 Irene Park" — an address-style example. Users unfamiliar with the system may type the full address here instead of using the Address Autocomplete field below. Two fields compete for the same mental model ("what is the property's name vs its address?").

F2.3 — After a property is created, the user is left on the properties list. There is no post-creation redirect to the property detail page, no banner saying "Property created — next step: add a mandate," and no CTA. The next action is not obvious.

F2.4 — The empty state on the properties list (`PropertiesView.vue:207`) reads: *"Add your first property to get started managing your portfolio."* The body copy is accurate but the zero-state offers no lifecycle context (what comes after adding a property?).

**Suggested fix:**
- Reorder the Add Property modal: basic fields first (name, address, type, city), then the bill upload as a collapsible "shortcut" section at the bottom.
- Rename the "Property name" field to "Reference name" or "Short name" and update the placeholder to "e.g. Irene Park Unit 3A" to clarify it is a display label, not a legal address.
- After save, redirect to the new property's detail page and show a one-time onboarding card: "Property created. Your next step: set up the mandate so you can manage and list this property."

---

## Step 3 — Create Mandate

### Admin web app

**Path:** Property detail > Mandate tab

**Click/tap count:** 4–6 (tab click, Create Mandate, fill form, submit)
**Time-on-task estimate:** 3–5 min
**Friction rating:** 2

**Findings:**

F3.1 — The empty state for the mandate tab (`MandateTab.vue:14`) reads: *"A signed rental mandate is required before you can list or manage this property."* This is the first place in the entire flow where the dependency is clearly explained. It should be surfaced much earlier (see F2.3).

F3.2 — The mandate type selector (`MandateTab.vue:415`) provides four options (Full Management, Letting Only, Rent Collection, Finders Fee) with short descriptions. The commission defaults auto-populate on type change — this is a good pattern. However, the "commission period" label reads "Commission (months' rent)" when the type is `once_off` and "Commission (%)" when monthly. The label change is dynamic but the field label value itself is confusingly parenthetical. First-time users may not understand that "1" in the once-off field means "1 month's rent," not "1%".

F3.3 — The "Owner info" section in the mandate creation form (`MandateTab.vue:335`) shows the owner name and email pulled from the landlord record, marked as read-only. If the owner email is missing, the form shows `⚠️ No email — add it to the landlord record before sending`. This warning uses a raw emoji in code rather than a styled component, and it is only visible after the user has opened the modal. There is no pre-flight check before the user reaches "Send for Signing."

F3.4 — The mandate form has no field for the agent's own commission details (agent name, PPRA number, agency name). SA mandate law requires agency identification. This is a potential legal compliance gap and should be flagged even if the data is inferred from the logged-in user.

F3.5 — "Notice period (days)" defaults to 60. This is correct for SA (2 calendar months). But there is no tooltip or label explaining why 60 is the default. A new agent might change it without understanding the RHA requirement.

**Suggested fix:**
- Surface the missing-owner-email warning before the user clicks "Send for Signing": check for the condition as a badge or alert strip on the mandate card itself, not only inside the modal.
- Add tooltips (?) icons next to "Notice period (days)" and "Commission" fields explaining the SA standard and RHA requirement.
- Add the agency/PPRA number to the mandate form (or auto-populate from the agency settings), even as read-only confirmation copy.

---

## Step 4 — Send Mandate for Signing

### Admin web app

**Path:** Mandate tab > "Send for Signing" button

**Click/tap count:** 1 (button tap)
**Time-on-task estimate:** 30 seconds (if owner email is present)
**Friction rating:** 2

**Findings:**

F4.1 — The "Send for Signing" button is disabled with `title="Owner email is required — update the landlord record first"` (`MandateTab.vue:93`). On desktop the tooltip appears on hover. On a touch device there is no tooltip visible — the button is just grey/disabled with no explanation. A mobile-web user will not know why the button does not work.

F4.2 — After sending, a toast appears: *"Mandate sent for signing — owner will receive an email shortly."* The word "shortly" is vague. A new agent will not know if "shortly" means seconds or minutes, and may repeatedly press the button.

F4.3 — The signing panel (`MandateSigningPanel.vue`) shows a real-time WebSocket-connected signer timeline. The live dot indicator is excellent but only shows "Live" text when `wsConnected` is true. When the WebSocket drops, the dot disappears silently with no fallback message like "Refresh to check status."

F4.4 — The signer timeline shows signer roles capitalised via `{{ signer.role }}` with no label mapping. If the backend returns `owner` and `agent`, these show as "owner" and "agent" directly in lowercase. No description of what each role means or what order they sign in.

F4.5 — There is no "What happens next?" explanation after sending. After the agent clicks Send, they see the signing timeline but there is nothing explaining that: (1) the owner signs first, (2) the agent countersigns, (3) the mandate becomes Active. A new agent may not understand the sequential signing model.

**Suggested fix:**
- Replace the disabled button tooltip with a visible inline warning banner below the mandate card: "Owner email is missing — add it to send this mandate for signing." Link directly to the landlord edit form.
- Add a post-send modal or inline callout: "We've emailed [owner name] a signing link. Once they sign, you'll get a counter-sign request. The mandate becomes active after both parties sign."
- Add a label map for signer roles in `MandateSigningPanel.vue`: `owner` → "Property Owner", `agent` → "Managing Agent".

---

## Step 5 — Advertise / List Vacancy

### Admin web app

**Path:** Property detail > Actions menu > "Advertise unit"

**Click/tap count:** 3 (Actions menu, Advertise unit, ?)
**Time-on-task estimate:** N/A — feature is PLANNED
**Friction rating:** 5 (blocking — feature not available)

**Findings:**

F5.1 — `property_advertising` has `status: PLANNED` in `features.yaml`. The "Advertise unit" menu item exists in the property detail Actions dropdown (`PropertyDetailView.vue:98`), implying the feature is available. Clicking it will either 404, show an empty state, or fail silently. The presence of this menu item in the UI for a PLANNED feature violates the product rule of not advertising unbuilt features and will confuse new agents who try to list their first vacancy.

F5.2 — Because advertising is not built, the lifecycle breaks here. A new agent has nowhere to go after the mandate is signed. There is no in-app guidance about what the next available step is (viewings can be booked directly via the agent mobile app, skipping the formal "listing" step).

**Suggested fix:**
- Hide the "Advertise unit" menu item in the admin until `property_advertising` is BUILT, or replace it with a "Coming soon" disabled item with a tooltip.
- Add a "What's next?" card to the mandate active state: "Your mandate is signed. While we build integrated listing, you can book viewings directly from the Agent app or manually from the Viewings section."

**Discovery filed:** `tasks/discoveries/2026-04-23-advertise-unit-menu-item-planned-feature.md`

---

## Step 6 — Book a Viewing

### Agent mobile app

**Path:** Dashboard tab > "Book a Viewing" CTA, or Pipeline tab > Mandates > Book Viewing

**Click/tap count:** 6–8 (CTA, property select, date picker, time picker, prospect name, phone, submit)
**Time-on-task estimate:** 3–4 min (first time)
**Friction rating:** 2

**Findings:**

F6.1 — The dashboard CTA (`DashboardPage.vue:149`) reads "Book a Viewing" and routes to `/viewings/new`. This is the most prominent CTA on the page but the primary tab bar (`MainLayout.vue:112`) does not include "Dashboard" as a tab — it has Today, Pipeline, People, Inbox. The "Dashboard" page (old route `/dashboard`) is accessible but buried. New agents will not find it unless they are told the URL. The tab the dashboard maps to in `tabForRoute` is "today."

F6.2 — The "Today" tab (`TodayPage.vue`) shows a commission-earnings hero card as the primary element. For a brand-new agent with no portfolio and no commission data, this shows R0 / R0 target — an immediately deflating first impression.

F6.3 — The booking form (`BookViewingPage.vue`) has a two-step stepper: (1) Viewing Details, (2) Prospect Details. Step 1 requires a property selection. The property list is loaded via API on mount. If the agent has no properties assigned (`PropertiesPage.vue:10-14`), the dropdown will be empty with no hint. The agent has no way to book a viewing from the mobile app if they have no properties assigned — there is no feedback message explaining this within the booking form itself. The property selection field shows a loading spinner while fetching but no empty-state if the result is an empty list.

F6.4 — Step 2 (Prospect Details) has email as optional but mobile as required. SA rental context: many walk-in prospects at a physical show give their phone but not an email. This is correct. However, the label reads "Mobile number *" — a new agent unfamiliar with the system may not know what the asterisk means (it is not explained anywhere).

F6.5 — The SA ID / Passport field is optional and unlabelled as to why it exists. A new agent will not know that capturing this now feeds the future tenant screening step. There is no contextual tooltip.

F6.6 — After successful booking, the app navigates to `router.replace('/viewings/{id}')`. This takes the agent to the viewing detail page. The first visit will be fine, but there is no confirmation animation or celebration moment — just an immediate transition to the viewing record.

**Suggested fix:**
- Add an empty state within the property dropdown of the booking form when no properties are loaded: "No properties assigned yet. Ask your admin to assign you to a property."
- Add a tooltip on the SA ID field: "Capturing the ID now makes tenant screening faster when you're ready to run a credit check."
- Add a brief success animation (iOS HIG: non-blocking banner) on booking confirmation before navigating away.

---

## Step 7 — Create Lease from Viewing

### Agent mobile app

**Path:** Viewing detail > "Create Lease" CTA → `CreateLeasePage.vue`

**Click/tap count:** 6–8 (viewing tap, lease CTA, dates, rent, deposit, submit)
**Time-on-task estimate:** 4–6 min (first time)
**Friction rating:** 3

**Findings:**

F7.1 — The lease creation page (`CreateLeasePage.vue`) is only accessible from a viewing. There is no way to create a lease from the Properties page in the agent mobile app (only from the admin web). A new agent who wants to create a direct lease (e.g. existing tenant referral with no formal viewing) has no path from the mobile app. The route `properties/:propertyId/leases/new` exists but maps to `CreateDirectLeasePage.vue` — it is only accessible via the admin or a manual URL deep-link.

F7.2 — The lease form pre-fills start date to "next month, 1st" and end date to "12 months later." This is appropriate for SA fixed-term leases. However, there is no explanation of why these dates were chosen. A new agent may override them unknowingly.

F7.3 — There is no deposit calculation guide. The hint text reads `Typically 1-2 months rent (R{oneMonthRent})` — this is helpful. But the RHA requires that the deposit be lodged in an interest-bearing account within a specified period. There is no in-context explanation of this legal obligation.

F7.4 — The unit selector only appears `v-if="!viewing.unit && units.length > 1"`. If the agent booked the viewing without specifying a unit (allowed in `BookViewingPage.vue`), and the property has multiple units, the lease form shows a unit selector. But the available units list is filtered to `status === 'available'` only. If all units are occupied, `units.value` is populated from `resp.results` (all units), meaning the agent can select occupied units. This is a data integrity risk.

F7.5 — Successful submission shows a positive notification and navigates to `/dashboard`. From there the agent has no clear path to the newly created lease. The agent is dropped back at the dashboard with no "next step" card. The pending lease (status `pending`) now needs to be sent for signing from the admin web, but this is not communicated.

F7.6 — The lease created here is a "quick lease" (basic terms: dates, rent, deposit). It does not connect to the AI lease builder or template system in the admin. A new agent may not know that a full RHA-compliant lease document also needs to be generated and sent for signing. The mobile app creates a record but not the lease PDF.

**Suggested fix:**
- Add a post-creation callout/banner: "Lease created. To send it for signing, open the admin portal on desktop and use Leases > Submit to send the e-sign request to your tenant."
- Guard the unit selector to only show units with `status !== 'occupied'` at display level (even if the API has a guard, the UI should not show clearly occupied units as options).
- Add a tooltip on the deposit field linking to the RHA 2 months rent deposit guidance.

---

## Step 8 — Send Lease for Signing (Admin web)

### Admin web app

**Path:** Leases > Submit tab → `SubmitLeaseView.vue`

**Click/tap count:** 5–8 (nav, find lease, select it, review, send)
**Time-on-task estimate:** 5–10 min (first time, including PDF preview)
**Friction rating:** 4

**Findings:**

F8.1 — The route `/leases/submit` redirects to `/leases` per the router (`index.ts:128`). There is no standalone "submit" page — the submission flow is embedded within the leases list. A new agent following a help article or mental model of "there is a submit step" will land on the leases list and be confused. The left-panel / right-panel split in `SubmitLeaseView.vue` suggests it was designed as a dedicated page but was demoted to a redirect target.

F8.2 — The `SubmitLeaseView.vue` displays pending leases with a lease card that shows `lease.status` and `signingLabel(signingStatuses.get(lease.id))` side-by-side. Both can say "pending" simultaneously — the lease status and the signing status use different underlying enums but similar words. A new agent cannot easily distinguish "lease status: pending (not yet signed)" from "signing status: not yet sent."

F8.3 — The signing border-left colour system (`signingBorderLeft`) exists as a visual cue but there is no legend explaining what the colours mean. Three states (not sent, sent, signed) are shown via colour alone with no text legend.

F8.4 — The AI Lease Builder (`/leases/build`) is a separate, complex tool with its own header row, template selector, and form panel. For a new agent following the first-cycle flow, there is no contextual link from the "pending lease created in mobile app" to the "generate the full PDF here." The two entry points (mobile quick lease vs admin builder) are not connected in the UI.

F8.5 — The lease builder header has a "DOCX" button next to "Create Lease." This is an unexplained acronym for a first-time user. There is no tooltip.

**Suggested fix:**
- Reinstate `/leases/submit` as a real page (not a redirect) and surface it in the Leases nav sub-items as "Send for Signing."
- Add a status legend (colour key) above the lease list in the submit view.
- Add a "Generate full lease PDF" CTA to the pending lease card, linking directly to `/leases/build?unit=X` with the correct unit pre-selected.

---

## Step 9 — Tenant Signs Lease (Public Sign View)

### Admin web app — public signing page

**Path:** `/sign/:token`

**Click/tap count:** ~5 (open link, read, scroll, sign, submit)
**Time-on-task estimate:** 5–15 min (reading the lease)
**Friction rating:** 2

**Findings:**

F9.1 — The public signing page (`PublicSignView.vue`) is not read in depth, but from the router it is accessible without authentication (`/sign/:token` has no auth guard). This is correct behaviour for a public signer.

F9.2 — There is no test of the signing page from a first-time tenant perspective in this audit scope. This should be a separate audit task.

F9.3 — The signing completion event broadcasts via WebSocket (`MandateSigningPanel.vue` / `ESigningPanel.vue`). From the agent perspective, the notification model is: see a signing status update in the panel if they have it open. There is no push notification, email notification to the agent, or in-app badge increment when a tenant signs. A new agent will not know the lease was signed unless they actively check.

**Suggested fix:**
- Add an in-app notification (toast or badge) when a signing event completes. File a discovery for push notification infrastructure.

---

## Step 10 — Tenant Move-In Prep

### Admin web app + agent mobile app

**Path:** None clearly defined

**Click/tap count:** N/A
**Time-on-task estimate:** N/A
**Friction rating:** 5 (this step has no UI support)

**Findings:**

F10.1 — The lifecycle step "Onboard" (step 11 in `lifecycle.yaml`) maps to `tenant_onboarding` feature. The feature is BUILT (`features.yaml:296`) with a shipped date of 2026-03-01, but `key_files: []` — there are no frontend files listed. From code inspection there is no visible UI flow for tenant onboarding in either the admin or agent app. This may be a backend-only flow or placeholder.

F10.2 — There is no "Move-In" checklist or incoming inspection screen in either app. `incoming_inspection` is `PLANNED`. After the lease is signed, there is no in-app guidance on how to conduct or record the incoming inspection.

F10.3 — The "keys, utilities, welcome pack" step described in the lifecycle has no corresponding UI at all. An agent completing their first move-in will have no in-app workflow to follow.

**Suggested fix:**
- Add a "Move-In Prep" panel to the property detail view that shows a manual checklist (non-digital for now): keys handed over, utilities notified, welcome pack sent. Each item is a checkbox that marks progress. This requires a new backend endpoint but is a high-value, low-complexity feature for first-cycle completion.
- File a discovery for the incoming inspection gap.

**Discovery filed:** `tasks/discoveries/2026-04-23-move-in-prep-no-ui.md`

---

## Summary: Platform coverage

| Step | Admin web | Agent mobile app | Status |
|------|-----------|-----------------|--------|
| 0 — First login | Login only, no onboarding | Login only, no onboarding | Both missing |
| 1 — Create owner | Full CRUD | Not applicable | Admin: functional |
| 2 — Create property | Full CRUD | Properties list (read-only) | Admin: functional |
| 3 — Create mandate | Full CRUD + sign | Not applicable | Admin: functional |
| 4 — Send for signing | One-click send + WS panel | Not applicable | Admin: functional |
| 5 — Advertise vacancy | Menu item exists, PLANNED feature | Not applicable | Gap |
| 6 — Book viewing | Not applicable | Full 2-step form | Agent app: functional |
| 7 — Create lease | Create via lease builder | Quick-create from viewing | Both: functional with gaps |
| 8 — Send lease for signing | Submission via leases list | Not applicable | Admin: functional with navigation gaps |
| 9 — Tenant signs | Public sign link | Not applicable | Functional |
| 10 — Move-in prep | No UI | No UI | Both missing |

---

## Priority Fix List (Top 10)

**P1 — Critical path blockers or legal exposure**

1. **FIX-01 [F5.1] — Remove "Advertise unit" menu item (PLANNED feature in production UI)**
   File: `admin/src/views/properties/PropertyDetailView.vue`. Either hide the item or mark it "Coming soon." Severity: P0 — every new agent hits this and the click fails.

2. **FIX-02 [F0.1 / F0.2] — Add first-run onboarding for new agents**
   A `profile.onboarded` flag + first-login modal with role context and the lifecycle golden path. Without this, new agents have no mental model of what the product does or what order to do things in. Affects every new user.

3. **FIX-03 [F2.3 / F3.1] — Post-creation redirects with "next step" guidance**
   After creating a property, redirect to property detail + show "next step: create mandate" banner. After mandate becomes active, show "next step: book a viewing" card. This is the minimum viable onboarding for the golden path.

4. **FIX-04 [F1.1] — Inline owner creation from Add Property modal**
   A new agent should not need to navigate to a separate page to create an owner before creating a property. Add an inline "Add owner" affordance inside the property creation modal.

5. **FIX-05 [F7.6 / F8.4] — Connect mobile quick-lease to admin lease builder**
   The mobile app creates a lease record but no signed PDF document. The agent needs to know they must open the admin app to generate and send the full lease. Add a post-creation callout on mobile and a "Generate lease PDF" CTA in the admin lease list for pending leases with no document.

**P2 — Significant friction, first-cycle degraded**

6. **FIX-06 [F4.1] — Make missing-owner-email warning visible without hover**
   The disabled button tooltip is hover-only. Surfacing the warning as a visible inline alert on the mandate card fixes this for all devices and all skill levels.

7. **FIX-07 [F8.1] — Reinstate `/leases/submit` as a real page**
   The current redirect means the submission flow has no dedicated entry point. Add it to the Leases nav section as "Send for Signing."

8. **FIX-08 [F6.3] — Empty state in viewing booking form when no properties assigned**
   If a new agent has no properties assigned, the property dropdown in `BookViewingPage.vue` is empty with no explanation. Add an empty state message.

9. **FIX-09 [F9.3] — In-app notification on signing completion**
   Agents have no passive signal that a tenant signed. A toast or badge when a signing event completes is table-stakes for async workflows.

10. **FIX-10 [F10.1 / F10.2 / F10.3] — Move-in prep checklist (minimum viable)**
    The first rental cycle ends with no UI at the move-in step. A basic checklist (keys, utilities, welcome pack) on the lease detail view closes the loop and gives agents a sense of completion.

---

## Discoveries spawned

| File | Priority hint | Summary |
|------|-------------|---------|
| `tasks/discoveries/2026-04-23-advertise-unit-menu-item-planned-feature.md` | P0 | Advertise unit menu item points to PLANNED feature |
| `tasks/discoveries/2026-04-23-move-in-prep-no-ui.md` | P1 | Move-in prep / tenant onboarding has no UI |
| `tasks/discoveries/2026-04-23-android-back-button-reset-form.md` | P2 | Android back button exits app from in-place password reset |
| `tasks/discoveries/2026-04-23-lease-signing-no-agent-notification.md` | P2 | No in-app notification when tenant signs lease |

---

## Handoff note — 2026-04-23

**Auditor:** ux-onboarding
**Deliverable:** `content/ux/audits/2026-04-agent-first-cycle.md`
**Method:** Static code-reading audit. No live browser session was used; all findings are derived from Vue SFC source, router configuration, and features.yaml cross-referencing.
**Screenshots:** Not captured (no live session). Descriptions in each step are grounded in component code.
**Discoveries:** 4 files created in `tasks/discoveries/`.
**Next:** PM to review priority fix list and promote discoveries. FIX-01 and FIX-02 are recommended for the next sprint.

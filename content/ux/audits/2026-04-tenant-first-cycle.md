---
audit_id: UX-002
audited_by: ux-onboarding
audit_date: 2026-04-23
app: tenant web app (tenant/)
viewport: 375×812 (iPhone 14 equivalent, portrait)
scope: invite email → first app launch → lease signing → rent payment discovery → maintenance via chat
---

# UX Audit: Tenant First Cycle

## Overview

This audit traces the journey a brand-new tenant takes from receiving their invite email through to logging their first maintenance request. The audit is based on code reading of `tenant/` (the active Vue 3 tenant web app), `backend/apps/accounts/`, `backend/apps/leases/`, `backend/apps/tenant/`, and `content/emails/`.

The `web_app/` directory referenced in the task has been replaced by `tenant/` — see the note at the end of this document.

Friction ratings: 1 = minor polish, 2 = noticeable friction, 3 = user likely to abandon or call the agent.

---

## Step 1 — Invite email

**What happens**

The agent triggers an invite from the admin app. The `invite_tenant` email template sends a single CTA: "Accept invitation" pointing to `invite_url`.

**Friction: 3 — BLOCKING (discovery filed)**

The `invite_url` links to a route that does not exist in the tenant app. There is no `/invite/:token` route in `tenant/src/router/index.ts`. A tenant clicking the link lands on the generic `LoginView` with no context, no pre-filled email, and no way to set a password.

Secondary friction: the email body is one sentence. It says "Your agent has invited you to manage your tenancy" but does not name the agent, explain what Klikk is, mention that the link expires in 72 hours, or tell the tenant what to expect. The 72-hour expiry exists only as a `note` field in the template frontmatter — it is not rendered in the email body.

**Suggested fix**
- Implement `/invite/:token` route and view (see discovery `2026-04-23-tenant-no-invite-accept-screen.md`)
- Expand invite email body: who sent it, what Klikk does (one sentence), what happens when they click, that the link expires in 72 hours, and a support email if it does not work

---

## Step 2 — First app launch (SplashView → LoginView)

**What happens**

`SplashView` shows the Klikk wordmark and a spinner. It checks `auth.isAuthenticated`: if false it redirects immediately to `LoginView`. `LoginView` shows "Welcome back" as the header.

**Friction: 2**

"Welcome back" is wrong language for a brand-new user who has never logged in before. There is no differentiation between a returning user and a first-time user at this stage.

The login form uses a flat list-row pattern (iOS Settings style): a label on the left, an input on the right. This is clean but the `Email` label is 20 characters wide and the input right of it has no visible border or background — on a white phone background, a first-time user may not immediately see that the field is tappable.

There is no "Forgot password?" link. A tenant who has had a password set for them by an agent (workaround until the invite-accept screen exists) has no self-service recovery path from the login screen.

**Suggested fixes**
- Change the LoginView header to "Sign in to Klikk" or "Your tenant portal" — neutral language that works for both first and returning users
- Add "Forgot your password?" text link below the sign-in button, pointing to a reset flow
- Add a subtle background tint (`bg-gray-50`) to the input rows to make them visually distinct from the container card

---

## Step 3 — First-time home screen (WelcomeView)

**What happens**

After login, the router guards redirect a new tenant (`seen_welcome_at` is null) to `WelcomeView` instead of `HomeView`. `WelcomeView` shows an onboarding checklist: Welcome pack, Deposit received, First rent scheduled, Keys handed over, Emergency contacts. A progress bar tracks completion.

**Friction: 1**

This is the strongest screen in the first-run flow. The pattern — a named checklist with a progress bar and a clear "all done" state — is correct. The copy is human and appropriate.

Minor issues:
- The fallback heading when the tenant's name is not available is "Hi there" which is fine, but it only shows the first name when available. If the full name is "Jan van der Berg" it renders "Jan" — correct and good.
- If the API call to `/tenant/onboarding/` fails silently (the code catches and swallows all errors), the view shows a generic "Your agent will begin the onboarding process shortly." This is acceptable but gives no indication of whether the silence is a network error or genuinely no data yet. A first-time user cannot tell the difference.
- The "Continue to dashboard" nudge link appears when onboarding is incomplete. This text implies that continuing to the dashboard before the checklist is done is optional. This is intentional but may cause tenants to skip past the welcome screen before their agent has sent the welcome pack.

**Suggested fixes**
- On API error, show a "Could not load your checklist. Pull to refresh." message rather than silent fallback
- Consider adding the agent's name to the hero copy: "Your agent Sarah is working through the checklist below" — requires agent name to be included in the onboarding payload

---

## Step 4 — Home dashboard (HomeView)

**What happens**

The home tab shows: greeting header, an optional "Lease ready to sign" CTA (when a pending signing submission exists), an "Active Repairs" section, and a "Your Unit" section showing up to 3 unit info items. A pink FAB in the bottom right opens the AI chat.

**Friction: 2**

**The signing CTA detection is fragile.** The dashboard makes three separate API calls: maintenance, unit-info, then leases, then for each lease it calls esigning submissions. This waterfall adds latency. On a slow 3G connection (common in SA), the signing CTA may not appear for 3–5 seconds after the rest of the page has loaded. A tenant who taps "Lease" from the tab bar before the CTA loads will not know to come back to Home.

**The AI chat FAB has no label.** It is a pink circle with a `MessageCircle` icon. First-time users on mobile do not know what it does. There is no tooltip, coach mark, or label.

**"Your Unit" empty state is invisible on first load.** If `unit-info` returns empty (the agent has not yet added unit info), the section header "Your Unit" and the "More info" link render above an empty space. There is no empty-state copy for this section — the loading skeleton shows four skeleton rows, then they disappear and nothing replaces them.

**Suggested fixes**
- Consider polling or a short timeout approach for the signing CTA rather than a pure waterfall, so it appears as soon as the data is available
- Add a coach mark or label on the FAB on first visit: "Chat with your AI assistant" with a one-time dismiss
- Add empty-state copy under "Your Unit" when no info items exist: "Your agent will add your Wi-Fi, access codes, and utility info here"

---

## Step 5 — Lease tab (LeaseView)

**What happens**

The Lease tab shows lease details (status, property, monthly rent, deposit, period), a monthly calendar with rent-due dots, a utilities section, and a unit info section (mirrored from HomeView). A "Lease ready to sign" CTA appears if a pending submission exists for this tenant.

**Friction: 3 — BLOCKING (discovery filed)**

**There are no rent payment instructions.** The lease shows the monthly rent amount (e.g. "R 8 500,00") and the due day (e.g. "due 1st") but there is no bank account, no account number, no branch code, and no payment reference. A first-time tenant looking at this screen cannot determine where to pay their rent.

The `payment_reference` field exists on the `Lease` model and is serialised. The `BankAccount` model on `Property`/`Landlord` holds full banking details. Neither is exposed in the tenant-facing lease endpoint or rendered here. This is the most critical gap in the first rental cycle from a tenant perspective.

**Secondary friction:** The lease "Status" row shows the raw string value capitalized (e.g. "pending", "active"). There is no plain-English explanation of what these statuses mean to the tenant. A "pending" lease is one that has been created but not yet signed. A first-time tenant does not know this.

**Suggested fixes**
- Add a "How to pay rent" section to LeaseView: bank name, account number, branch code, account holder, unique payment reference (tap-to-copy)
- Add a status description row: "Pending — waiting for all parties to sign" / "Active — your lease is in force"
- See discovery `2026-04-23-tenant-no-rent-payment-instructions.md`

---

## Step 6 — Lease signing (LeaseSigningView)

**What happens**

Accessible from the signing CTA on Home or Lease, or from Settings > Lease & Signing. Shows a lease card with status badge, then a "Signing Status" section listing all signers (check/clock/X icons) and a "Sign Now" button if it is this tenant's turn. Tapping "Sign Now" opens the signing URL in a new browser tab (web) or Capacitor Browser (native).

**Friction: 3 (discovery filed)**

**After signing, there is no return path.** The external tab/browser shows the DocuSign-style signing interface (Klikk native e-sign). After the tenant completes signing, the external page has no redirect configured back to the tenant portal. The tenant ends up in a dead tab. The signing CTA on the Home dashboard only clears on the next full page load — there is no in-app confirmation.

**Additional friction:** The page title is "Lease & Signing" (in `AppHeader`) which is clear, but the route label in `SettingsView` is also "Lease & Signing" — this is consistent. However, accessing this view from the "Lease" tab (LeaseView) navigates to a different route (`/signing`) rather than scrolling down within the Lease tab. This is a subtle inconsistency: the Lease tab has its own signing CTA that navigates to `/signing`, which then shows a minimal version of the lease card again. The tenant sees lease info twice.

**Suggested fixes**
- Implement a post-sign return URL that brings the tenant back to the portal (see discovery `2026-04-23-tenant-signing-opens-external-tab.md`)
- Consider merging `LeaseSigningView` into the existing `LeaseView` rather than a separate route, or at minimum ensure the navigation path is consistent
- Add a "What happens next?" explainer on the signing screen: "Once all parties sign, your lease becomes active and you'll receive a copy by email"

---

## Step 7 — Rent payment (no dedicated screen exists)

**What happens**

There is no rent payment screen, payment history, or receipt view in the tenant app. The Lease tab shows the rent amount and due date. That is the entirety of the rent payment UX.

**Friction: 3**

A tenant who wants to confirm whether their payment was received, download a receipt, or see their payment history has no in-app path. The `rent_tracking` feature is BUILT (features.yaml) but nothing from it is surfaced in the tenant portal.

This is the second most critical gap after the missing payment instructions. Monthly rent is the heartbeat of the tenancy; tenants should be able to see the status of each month's payment without calling the agent.

**Suggested fix**
- Add a "Payments" section to LeaseView listing: this month's due date, amount, and payment status (paid/unpaid/overdue) sourced from the rent tracking backend
- Basic receipt download (PDF) when a payment is confirmed

---

## Step 8 — Reporting a maintenance issue (IssuesView → ReportIssueView)

**What happens**

The "Repairs" tab (Wrench icon in the tab bar) shows a filtered list of issues with a FAB to report a new one. `ReportIssueView` has four fields: Title, Category (dropdown), Priority (dropdown), Description. On submit, the user is redirected to the issue detail view.

**Friction: 1**

This flow is the cleanest in the app. The form is minimal and the category and priority dropdowns are sensible defaults.

Minor issues:
- The priority default is "medium". A first-time user reporting a burst pipe may not know to change this to "urgent". There is no helper text explaining what the priority levels mean or when to use "urgent".
- The Category field has "Select..." as a placeholder and no default value. If the tenant submits without picking a category, the validation message is "Please fill in the title and description" — the category validation is silently missing from the `submit()` function. An empty category will be sent to the API.
- The description field has a placeholder "Describe the issue in detail..." but no character minimum. One-word descriptions like "broken" will pass.

**Suggested fixes**
- Add helper text for priority: "Urgent = safety risk or no water/power; High = major inconvenience; Medium = needs attention soon; Low = when convenient"
- Add category to the required field check in `submit()` and show a validation error if empty
- Add a minimum description length of 20 characters with inline feedback

---

## Step 9 — AI chat as maintenance triage path (ChatDetailView)

**What happens**

The AI chat is accessible via the FAB on HomeView and via Settings. `ChatDetailView` shows a standard chat UI with message bubbles, a typing indicator, and a "confirm ticket" card that appears when the AI decides a repair should be logged. The confirm card has a description and two buttons: "Yes, log it" and "Not now".

A unique touch: when the confirm ticket card is tapped, it redirects to `ReportIssueView` with the AI-drafted title pre-filled via `route.query.title`.

**Friction: 2**

**The chat is not discoverable.** On HomeView, the FAB is unlabelled (see Step 4). On the Repairs tab, there is no suggestion that chatting with the AI is an alternative way to report an issue — the only CTA is the "+" FAB which goes straight to the manual form. A tenant who has seen the AI chat on Home may not connect it to the Repairs workflow.

**The confirm ticket card shows the AI's description** but the tenant cannot edit it before confirming. The redirect to `ReportIssueView` pre-fills only the title. The description must be filled in again manually. If the AI has generated a good description, the tenant has to re-type it.

**The chat list empty state is not helpful** (see discovery `2026-04-23-tenant-chat-no-empty-state-prompt.md`).

**Suggested fixes**
- On the Repairs empty state, add a line: "Not sure what to log? Chat with the AI assistant" with a link to start a new chat
- Pass the AI-drafted description as a query parameter in addition to the title when redirecting to `ReportIssueView`
- Add 2–3 suggested starter prompts to the ChatListView empty state

---

## Step 10 — Issue detail and status tracking (IssueDetailView)

**What happens**

Issue detail shows a meta card (category, status, priority, logged date) and a chat-style activity feed for the issue. A WebSocket connection shows the live status. The tenant can send messages and attach photos. System messages (status changes) appear as centred pills.

**Friction: 1**

This is well built. The WebSocket connection indicator ("Connecting...") is shown when the connection is not yet established, which is honest feedback.

One gap: when the issue is resolved or closed by the agent, there is no clear "your issue has been resolved" end state. The status badge updates to "resolved" but there is no modal, toast, or banner acknowledging the resolution. A tenant may not notice the status badge has changed.

**Suggested fix**
- When the WebSocket receives a `status_change` activity where the new status is "resolved" or "closed", show a brief toast or a full-width success card: "Your repair has been resolved. Let us know if the problem continues."

---

## Navigation structure findings

The tab bar has four items: Home, Repairs, Lease, Settings. This is appropriate for the feature set.

**Missing: no way to navigate Home → Lease without the tab bar.** The home screen has a signing CTA and a "Your Unit" section that both say "More info" pointing to the Lease tab, but there is no direct deep link from the signing CTA on Home to the signing sub-screen — it goes to the Lease tab's root, which then requires a second tap on the signing CTA. Two taps to get to the sign button from the home screen.

**Chat is buried.** The AI chat has no tab bar entry. It is accessible via the unlabelled FAB on Home, via Settings > AI Assistant, or from the Repairs view (if the suggestion above is implemented). For a feature that is central to the onboarding story, this is low visibility.

---

## Priority fix list

| Priority | Finding | Discovery ref |
|----------|---------|---------------|
| P0 | No invite-accept screen — new tenants cannot register | `2026-04-23-tenant-no-invite-accept-screen.md` |
| P0 | Signing URL opens dead external tab with no return path | `2026-04-23-tenant-signing-opens-external-tab.md` |
| P1 | No rent payment instructions anywhere in the tenant portal | `2026-04-23-tenant-no-rent-payment-instructions.md` |
| P1 | No rent payment history or receipt view | (in audit body, step 7 — no separate discovery) |
| P2 | Invite email is too thin; 72h expiry not in body | `2026-04-23-tenant-invite-email-thin-copy.md` |
| P2 | Login screen says "Welcome back" on first visit; no forgot-password link | (in audit body, step 2) |
| P2 | AI chat FAB is unlabelled on first visit | (in audit body, step 4) |
| P2 | AI chat empty state gives no indication of capability | `2026-04-23-tenant-chat-no-empty-state-prompt.md` |
| P2 | Category field not validated on issue submission | (in audit body, step 8) |
| P3 | "Your Unit" section on Home has no empty state copy | (in audit body, step 4) |
| P3 | Lease status values shown as raw strings with no plain-English explanation | (in audit body, step 5) |
| P3 | Issue resolved/closed state has no in-app acknowledgement | (in audit body, step 10) |

---

## Note on app directory

The task spec references `web_app/` as the tenant web app. This directory has been archived to `.claude/old/web_app/` and is no longer active. The current tenant web app is `tenant/` — a Vue 3 + Tailwind progressive web app with Capacitor support for native deployment. All findings in this audit refer to `tenant/`.

---

## Files referenced in this audit

- `tenant/src/views/auth/SplashView.vue`
- `tenant/src/views/auth/LoginView.vue`
- `tenant/src/views/auth/TwoFAEnrollView.vue`
- `tenant/src/views/home/WelcomeView.vue`
- `tenant/src/views/home/HomeView.vue`
- `tenant/src/views/leases/LeaseView.vue`
- `tenant/src/views/esigning/LeaseSigningView.vue`
- `tenant/src/views/issues/IssuesView.vue`
- `tenant/src/views/issues/ReportIssueView.vue`
- `tenant/src/views/issues/IssueDetailView.vue`
- `tenant/src/views/chat/ChatListView.vue`
- `tenant/src/views/chat/ChatDetailView.vue`
- `tenant/src/views/settings/SettingsView.vue`
- `tenant/src/views/shell/AppShell.vue`
- `tenant/src/router/index.ts`
- `backend/apps/accounts/views.py`
- `backend/apps/leases/models.py`
- `backend/apps/properties/models.py`
- `backend/apps/tenant/models.py`
- `content/emails/invite_tenant.md`
- `content/emails/welcome_tenant.md`

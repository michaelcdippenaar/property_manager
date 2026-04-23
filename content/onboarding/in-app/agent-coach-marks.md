# In-App Coach Marks — Agent First Rental Cycle
**Version:** 1.0
**Date:** 2026-04-23
**Author:** ux-onboarding
**Audit source:** `content/ux/audits/2026-04-agent-first-cycle.md` (UX-001)
**Lifecycle reference:** `content/product/lifecycle.yaml` (steps 1–8)
**For frontend implementation:** see [Frontend Implementation Spec](#frontend-implementation-spec) at the end of this document.

---

## How to read this document

Each coach mark entry follows this structure:

| Field | Description |
|-------|-------------|
| **ID** | Unique stable ID (e.g. `CM-001`). Used in the `user_dismissed_coach_marks` backend field. |
| **Screen** | App + route where the mark appears |
| **Element** | DOM/component element the mark anchors to (or "screen overlay" if no anchor) |
| **Trigger** | Condition that causes the mark to appear |
| **Copy** | Exact tooltip / popover text (15 words max per rule; checked at end of each entry) |
| **Dismiss** | How the user closes this mark |
| **Don't-show-again** | Whether a "don't show again" control is present |
| **Max concurrent** | Maximum number of marks that can be visible simultaneously in this session |
| **Lifecycle step** | Which of the 15 lifecycle steps this mark supports |

**Global rule:** No more than 2 coach marks may be visible at the same time across the entire app. Marks are queued and surfaced one at a time if two or more are triggered by the same action.

---

## Phase A — Pre-Tenancy (Lifecycle Steps 1–7)

### CM-001 — First login: empty dashboard welcome

| Field | Value |
|-------|-------|
| **ID** | CM-001 |
| **Screen** | Admin web — `/dashboard` (or agent app — Today tab) |
| **Element** | Screen overlay (modal-style, centred, dark scrim behind) |
| **Trigger** | `profile.onboarded === false` — fires once on first successful login |
| **Copy** | "Start here: add a property, then invite the owner to sign the mandate." |
| **Word count** | 15 |
| **Dismiss** | Tap / click "Got it" button |
| **Don't-show-again** | Not needed — trigger is one-time flag (`profile.onboarded` set to `true` on dismiss) |
| **Max concurrent** | 1 (no other mark fires until this is dismissed) |
| **Lifecycle step** | Step 0 — Onboarding |

**Visual spec:** Full-screen scrim (opacity 0.6, navy). Card centred, white background, rounded-16. Klikk logo top, body copy, single CTA button in Accent pink labelled "Got it — show me around." Tapping "Got it" dismisses and sets `profile.onboarded = true` via PATCH `/api/v1/auth/profile/`.

---

### CM-002 — Owners list: empty state tooltip

| Field | Value |
|-------|-------|
| **ID** | CM-002 |
| **Screen** | Admin web — `/landlords` |
| **Element** | "Add Owner" primary button |
| **Trigger** | `owners.count === 0` AND `profile.onboarded` was just set to `true` (i.e. first session) |
| **Copy** | "Owners come first. Add the landlord before creating a property." |
| **Word count** | 11 |
| **Dismiss** | Tap the "?" close icon on the popover, or tap the "Add Owner" button (action = dismiss) |
| **Don't-show-again** | Yes — checkbox inside popover: "Don't show me this again" |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 0 — Onboarding |

**Visual spec:** Tooltip popover anchored below the "Add Owner" button. Arrow pointing up at button. Navy background, white text. Dismiss X in top-right corner.

---

### CM-003 — Add Property modal: owner dropdown empty state

| Field | Value |
|-------|-------|
| **ID** | CM-003 |
| **Screen** | Admin web — `/properties` > Add Property modal |
| **Element** | Owner dropdown (inside Add Property modal) |
| **Trigger** | Modal opens AND the owner dropdown options list is empty |
| **Copy** | "No owners yet. Add an owner first — they must be linked to every property." |
| **Word count** | 14 |
| **Dismiss** | Popover auto-dismisses when the user closes the modal, or can be dismissed with X |
| **Don't-show-again** | Yes |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 0 — Onboarding / Step 1 — Create property |

**Visual spec:** Inline warning strip (amber, not a floating popover) rendered inside the modal directly below the owner dropdown. Icon: info circle. Inline link "Add an owner" navigates to `/landlords` and opens the Add Owner form.

---

### CM-004 — Property created: next step card

| Field | Value |
|-------|-------|
| **ID** | CM-004 |
| **Screen** | Admin web — Property detail page (post-creation redirect) |
| **Element** | Top of property detail page — banner slot above tabs |
| **Trigger** | Property detail page loads AND `property.mandate_status === null` AND this property was created in the current session (passed via router state or query param `?new=1`) |
| **Copy** | "Property added. Next: set up the mandate so you can manage and list this property." |
| **Word count** | 14 |
| **Dismiss** | X button on the banner, OR user clicks the Mandate tab (action = dismiss) |
| **Don't-show-again** | Not needed — will not re-trigger once dismissed (stored in dismissed set) |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 1 — Notice (property ready for mandate) |

**Visual spec:** Full-width info banner, navy left-border, white background. Left: copy. Right: "Set up mandate →" CTA link that activates the Mandate tab. Dismiss X far right.

---

### CM-005 — Mandate tab: notice period tooltip

| Field | Value |
|-------|-------|
| **ID** | CM-005 |
| **Screen** | Admin web — Property detail > Mandate tab > Create Mandate modal |
| **Element** | "Notice period (days)" field label — inline (?) icon |
| **Trigger** | User focuses the "Notice period (days)" field for the first time (focus event, once-per-session) |
| **Copy** | "SA law requires 2 months (60 days). Don't change this without legal advice." |
| **Word count** | 13 |
| **Dismiss** | Click anywhere outside the tooltip |
| **Don't-show-again** | Yes — stored in dismissed set as `CM-005` |
| **Max concurrent** | 2 (may co-exist with CM-006 if agent tabs between fields) |
| **Lifecycle step** | Step 1 — Notice (mandate setup) |

**Visual spec:** Inline tooltip (not a modal). (?) icon rendered beside the field label. On hover/focus, tooltip appears above-right. Max width 220px. White card, navy text, drop shadow.

---

### CM-006 — Mandate tab: commission field tooltip

| Field | Value |
|-------|-------|
| **ID** | CM-006 |
| **Screen** | Admin web — Property detail > Mandate tab > Create Mandate modal |
| **Element** | "Commission" field label — inline (?) icon |
| **Trigger** | User focuses the Commission field for the first time (once per session) |
| **Copy** | "For once-off types, enter months of rent (e.g. 1 = one month's rent)." |
| **Word count** | 13 |
| **Dismiss** | Click anywhere outside the tooltip |
| **Don't-show-again** | Yes — stored in dismissed set as `CM-006` |
| **Max concurrent** | 2 |
| **Lifecycle step** | Step 1 — Notice (mandate setup) |

**Visual spec:** Same as CM-005.

---

### CM-007 — Mandate sent: what happens next

| Field | Value |
|-------|-------|
| **ID** | CM-007 |
| **Screen** | Admin web — Property detail > Mandate tab (after "Send for Signing" succeeds) |
| **Element** | Inline card below the signing timeline |
| **Trigger** | Mandate status changes to `sent` in the current session (WebSocket event or optimistic update) |
| **Copy** | "Owner signs first, then you countersign. Mandate goes active when both are done." |
| **Word count** | 14 |
| **Dismiss** | Dismiss X, or auto-dismiss when mandate status reaches `active` |
| **Don't-show-again** | No — contextual, fires once per mandate send action |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 1 — Notice (mandate in signing) |

**Visual spec:** Soft-blue info card, full width of the mandate tab content area. Icon: clock / hourglass. Dismiss X top-right.

---

### CM-008 — Mandate active: book a viewing prompt

| Field | Value |
|-------|-------|
| **ID** | CM-008 |
| **Screen** | Admin web — Property detail (when mandate status changes to `active`) |
| **Element** | Top of property detail page — banner slot |
| **Trigger** | `property.mandate_status === 'active'` AND the property has zero viewings recorded |
| **Copy** | "Mandate signed. You can now book viewings from the Agent app." |
| **Word count** | 11 |
| **Dismiss** | X button, or auto-dismiss after 10 seconds |
| **Don't-show-again** | Yes |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 3 — Viewings |

**Visual spec:** Same banner pattern as CM-004, but with a green left-border (success context). Right CTA: "Open Agent app" (deep link or QR code popover to install/open).

---

## Phase A — Viewings (Agent Mobile App, Lifecycle Step 3)

### CM-009 — Agent app: viewing booking — property dropdown empty

| Field | Value |
|-------|-------|
| **ID** | CM-009 |
| **Screen** | Agent app — `/viewings/new` > Step 1 > Property selector |
| **Element** | Property dropdown (below the label "Select property") |
| **Trigger** | `BookViewingPage` mounts AND the API returns zero properties |
| **Copy** | "No properties yet. Ask your admin to assign you to a property first." |
| **Word count** | 13 |
| **Dismiss** | Not dismissible — persists until properties load or user navigates away |
| **Don't-show-again** | N/A — this is a functional empty state, not a coach mark popover |
| **Max concurrent** | N/A |
| **Lifecycle step** | Step 3 — Viewings |

**Visual spec:** Replaces the loading spinner inside the dropdown. Shows a ghost-state inside the select box: icon (house outline) + copy. Not a floating tooltip — inline empty state within the form field container.

---

### CM-010 — Agent app: SA ID field tooltip

| Field | Value |
|-------|-------|
| **ID** | CM-010 |
| **Screen** | Agent app — `/viewings/new` > Step 2 > SA ID / Passport field |
| **Element** | SA ID / Passport field label — inline (?) icon |
| **Trigger** | User taps the (?) icon next to the SA ID field |
| **Copy** | "Capturing ID now speeds up tenant screening later. Optional for now." |
| **Word count** | 11 |
| **Dismiss** | Tap anywhere outside tooltip, or tap X |
| **Don't-show-again** | Yes |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 3 — Viewings (feeding Step 4 — Screen) |

**Visual spec:** Bottom-sheet style tooltip on mobile (slides up from bottom, 40% screen height). Title: "Why we ask for an ID." Body: coach mark copy. Close button. Navy header, white body.

---

## Phase A — Lease (Lifecycle Steps 5–6)

### CM-011 — Agent app: deposit field RHA guidance

| Field | Value |
|-------|-------|
| **ID** | CM-011 |
| **Screen** | Agent app — `/viewings/:id/lease/new` (CreateLeasePage) |
| **Element** | Deposit amount field — inline (?) icon |
| **Trigger** | User taps the (?) icon next to the Deposit field |
| **Copy** | "RHA requires deposit in an interest-bearing account within 7 days of receipt." |
| **Word count** | 14 |
| **Dismiss** | Tap outside or tap X |
| **Don't-show-again** | Yes |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 7 — Deposit |

**Visual spec:** Same bottom-sheet pattern as CM-010.

---

### CM-012 — Agent app: lease created — go to admin to send

| Field | Value |
|-------|-------|
| **ID** | CM-012 |
| **Screen** | Agent app — success state after lease creation (before router.replace) |
| **Element** | Full-screen success state overlay (between form submit and navigation) |
| **Trigger** | Lease creation API call returns `201` |
| **Copy** | "Lease saved. Open the Klikk admin on desktop to generate the PDF and send for signing." |
| **Word count** | 15 |
| **Dismiss** | Tap "Got it" button (then app navigates to dashboard) |
| **Don't-show-again** | Yes — "Don't remind me" checkbox on this screen |
| **Max concurrent** | 1 (blocks navigation) |
| **Lifecycle step** | Step 5 — Lease |

**Visual spec:** Full-screen success card (not a floating modal). Navy background. Checkmark icon in Accent pink. Copy centred. Two buttons: "Got it" (primary, navigates home) and "Don't remind me again" (text link, sets dismissed flag then navigates home). This is the one mark that deliberately blocks navigation briefly — it is the most critical cross-platform handoff point in the first cycle.

---

## Phase B — Lease Signing (Admin Web, Lifecycle Step 5)

### CM-013 — Admin: pending lease — generate PDF prompt

| Field | Value |
|-------|-------|
| **ID** | CM-013 |
| **Screen** | Admin web — `/leases` (Leases list, or SubmitLeaseView) |
| **Element** | Pending lease card (lease.status === 'pending' AND no document attached) |
| **Trigger** | Lease card renders with `status === 'pending'` and `document === null` |
| **Copy** | "This lease has no PDF yet. Generate one in Lease Builder before sending to tenant." |
| **Word count** | 15 |
| **Dismiss** | Not a floating mark — this is inline copy on the lease card itself. Disappears when a document is attached. |
| **Don't-show-again** | N/A — contextual, state-driven |
| **Max concurrent** | N/A |
| **Lifecycle step** | Step 5 — Lease |

**Visual spec:** Amber inline strip directly below the lease card header. Icon: warning triangle. Text as above. Inline link: "Go to Lease Builder →" routes to `/leases/build?unit={unit_id}`.

---

### CM-014 — Admin: lease signing status legend

| Field | Value |
|-------|-------|
| **ID** | CM-014 |
| **Screen** | Admin web — `/leases` (SubmitLeaseView, lease list) |
| **Element** | Section header above lease list — inline (?) icon |
| **Trigger** | User visits the leases view for the first time (session-once) |
| **Copy** | "Colours show signing status: amber = not sent, blue = sent, green = signed." |
| **Word count** | 13 |
| **Dismiss** | Tap X on popover |
| **Don't-show-again** | Yes |
| **Max concurrent** | 1 |
| **Lifecycle step** | Step 5 — Lease |

**Visual spec:** Tooltip anchored to the (?) icon beside the section header "Pending leases." Shows a small colour key: three dots (amber, blue, green) with labels. Max width 280px.

---

## Global / Cross-Screen Marks

### CM-015 — Help icon persistent nudge (first session only)

| Field | Value |
|-------|-------|
| **ID** | CM-015 |
| **Screen** | Admin web — all pages (global) AND Agent app — all tabs |
| **Element** | Help / (?) icon in top-right nav bar |
| **Trigger** | `profile.onboarded` becomes `true` (just dismissed CM-001) AND user has not tapped the help icon in this session |
| **Copy** | "Stuck? Step-by-step guides are here — one for every part of the cycle." |
| **Word count** | 13 |
| **Dismiss** | Auto-dismiss after 8 seconds, or tap the help icon (action = dismiss + open help) |
| **Don't-show-again** | Yes — fires once per account lifetime |
| **Max concurrent** | 1 |
| **Lifecycle step** | All steps |

**Visual spec:** Animated pulse ring on the help icon (Accent pink, 2-pulse). Small tooltip above icon: copy as above. No scrim. Lightweight — does not block interaction.

---

## Summary table

| ID | Screen | Lifecycle step | One-line copy |
|----|--------|---------------|---------------|
| CM-001 | Admin / Agent app — first login | Step 0 | "Start here: add a property, then invite the owner to sign the mandate." |
| CM-002 | Admin — `/landlords` empty | Step 0 | "Owners come first. Add the landlord before creating a property." |
| CM-003 | Admin — Add Property modal | Step 0–1 | "No owners yet. Add an owner first — they must be linked to every property." |
| CM-004 | Admin — Property detail (new) | Step 1 | "Property added. Next: set up the mandate so you can manage and list this property." |
| CM-005 | Admin — Mandate modal: notice field | Step 1 | "SA law requires 2 months (60 days). Don't change this without legal advice." |
| CM-006 | Admin — Mandate modal: commission field | Step 1 | "For once-off types, enter months of rent (e.g. 1 = one month's rent)." |
| CM-007 | Admin — Mandate tab (sent) | Step 1 | "Owner signs first, then you countersign. Mandate goes active when both are done." |
| CM-008 | Admin — Property detail (active mandate) | Step 3 | "Mandate signed. You can now book viewings from the Agent app." |
| CM-009 | Agent app — viewing booking | Step 3 | "No properties yet. Ask your admin to assign you to a property first." |
| CM-010 | Agent app — SA ID field | Step 3→4 | "Capturing ID now speeds up tenant screening later. Optional for now." |
| CM-011 | Agent app — deposit field | Step 7 | "RHA requires deposit in an interest-bearing account within 7 days of receipt." |
| CM-012 | Agent app — lease created success | Step 5 | "Lease saved. Open the Klikk admin on desktop to generate the PDF and send for signing." |
| CM-013 | Admin — lease card (no PDF) | Step 5 | "This lease has no PDF yet. Generate one in Lease Builder before sending to tenant." |
| CM-014 | Admin — lease list header | Step 5 | "Colours show signing status: amber = not sent, blue = sent, green = signed." |
| CM-015 | Global — help icon | All | "Stuck? Step-by-step guides are here — one for every part of the cycle." |

**Total marks: 15. Max active at any one time: 2 (rule enforced globally).**

---

## Dismiss + "Don't show again" states — reference table

| State | Behaviour | Backend storage |
|-------|-----------|----------------|
| Dismissed this session | Mark hidden for the rest of the session; will re-appear on next login if not set as "don't show again" | In-memory (Pinia / Vue reactive state) |
| "Don't show again" checked | Mark never shown again for this account | `dismissed_coach_marks: [CM-001, CM-005, ...]` — array field on `UserProfile` model, stored as JSON |
| Auto-dismiss (timed) | Mark disappears after N seconds (CM-008: 10 s, CM-015: 8 s); same as session-dismiss — does not set "don't show again" | In-memory only |
| Action-dismiss | Performing the related action (e.g. clicking "Add Owner") also counts as a dismiss; sets session-dismissed | In-memory; promote to "don't show again" only if the user explicitly checked the box |
| One-time-flag marks (CM-001) | Trigger is the `profile.onboarded` flag — once flag is set to `true`, the trigger condition is permanently false. No separate dismissed storage needed. | `profile.onboarded` boolean on backend |

---

## Frontend Implementation Spec

> This section is addressed to the frontend developer who will implement these coach marks. A separate RNT task should be opened by PM once this spec is reviewed and approved.

### Data model — backend

**New field on `UserProfile` model (`backend/apps/users/models.py`):**

```python
dismissed_coach_marks = ArrayField(
    models.CharField(max_length=16),
    default=list,
    blank=True,
    help_text="List of coach mark IDs (e.g. CM-001) permanently dismissed by this user."
)
onboarded = models.BooleanField(
    default=False,
    help_text="True after agent completes first-login coach mark (CM-001)."
)
```

**API change:** include both fields in the `/api/v1/auth/profile/` GET response. Accept PATCH with:
- `onboarded: true` — sets onboarded flag
- `dismissed_coach_marks: ["CM-001", "CM-005"]` — replaces array (front-end sends the full updated list)

### Frontend — shared composable (`admin/src/composables/useCoachMarks.ts`)

```typescript
// Pseudocode — implement per project conventions
const { isDismissed, dismiss, dismissPermanently } = useCoachMarks()

// isDismissed(id) — returns true if:
//   a) id is in profile.dismissed_coach_marks (backend)  OR
//   b) id is in sessionDismissed set (in-memory)

// dismiss(id) — session-only dismiss (adds to sessionDismissed)
// dismissPermanently(id) — adds to profile.dismissed_coach_marks, PATCHes backend
```

### Frontend — CoachMark component (`admin/src/components/CoachMark.vue`)

Props:
```typescript
interface CoachMarkProps {
  id: string           // e.g. "CM-005" — looked up in isDismissed
  variant: 'tooltip' | 'banner' | 'modal' | 'inline-strip' | 'bottom-sheet'
  anchor?: string      // CSS selector for tooltip anchor element
  autoDismissMs?: number  // if set, auto-dismiss after N ms
  showDontAskAgain?: boolean  // render "Don't show again" checkbox
}
```

Emits: `@dismissed`, `@dismissed-permanently`

The component renders nothing if `isDismissed(id)` is true. This is the only gate needed — callers do not need to check.

### Agent app — mirrored composable (`agent-app/src/composables/useCoachMarks.ts`)

Same interface. Uses Quasar's `LocalStorage` as session store and calls the same REST endpoint for permanent dismissal.

### Concurrency guard

A global Pinia store (`admin/src/stores/coachMarks.ts`) tracks `activeMarkIds: string[]`. Before rendering, each `CoachMark` component checks `activeMarkIds.length < 2`. If at capacity, it queues itself and waits for a `dismissed` event before appearing.

### Implementation order (suggested)

1. Backend: add `onboarded` + `dismissed_coach_marks` fields + PATCH support.
2. Shared composable + Pinia store.
3. `CoachMark.vue` component (admin) + mirrored composable (agent app).
4. Wire in marks in order: CM-001 → CM-002 → CM-003 → CM-004 (first cycle critical path).
5. Wire in field-level marks: CM-005, CM-006, CM-010, CM-011, CM-014.
6. Wire in event-driven marks: CM-007, CM-008, CM-012, CM-013.
7. Wire in global mark: CM-015.
8. QA: test with a fresh account; verify max 2 concurrent; verify "don't show again" persists across sessions.

### Marks NOT in scope for v1 implementation

Steps 9–15 of the lifecycle (Move-Out, Repairs, Move-In, Active Tenancy, Renewal, Refund) are either PLANNED features or post-first-cycle. Coach marks for those steps should be authored in a follow-up UX task once the corresponding features are built.

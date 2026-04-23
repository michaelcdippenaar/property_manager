# UAT Protocol v1 — Klikk Admin App
**Version:** 1.0
**Session length:** 30 minutes
**Tester persona:** First-time property agent, no prior Klikk experience
**Facilitator:** MC (observer, not coach)

---

## Overview

This protocol covers the core agent rental flow from adding a property through to logging a maintenance ticket. It maps to steps 0–13 of the Klikk rental lifecycle. Each scenario is written as a task card — read the card aloud or place it in front of the tester, then stay silent.

---

## Pre-session checklist

Before the tester sits down, confirm:

- [ ] Fresh agent account registered and email-verified on staging
- [ ] No properties, units, or tenants exist (clean slate)
- [ ] At least one lease template is available in the lease builder
- [ ] Maintenance categories seeded: "Plumbing", "Electrical", "General"
- [ ] Clarity recording active (staging, consent banner will appear on first load)
- [ ] Observer note template open in a separate device or notebook
- [ ] Tester has signed the POPIA consent form (`uat-consent-form.md`)

---

## Scenario task cards

### Scenario 1 — Add a property

**Read to tester:**
> "You have just been given a new rental mandate for a property at 14 Oak Avenue, Stellenbosch. Add it to Klikk."

**What to watch for:**
- Does the tester find the "Add property" entry point without help?
- Does the tester understand what fields are required vs optional?
- Is the address input clear?

**Task passes when:** A property record appears in the property list with the correct address.

---

### Scenario 2 — Add a unit

**Read to tester:**
> "The property has one unit — a two-bedroom apartment on the ground floor. Add it."

**What to watch for:**
- Does "unit" mean anything to the tester, or do they expect "apartment" / "flat"?
- Does the tester know where to navigate after adding the property?
- Is the unit form discoverable from the property detail page?

**Task passes when:** A unit is visible under the property.

---

### Scenario 3 — Add a tenant

**Read to tester:**
> "You have a prospective tenant: Sarah Botha, sarah.botha@gmail.com, 082 456 7890. Add her as a tenant in Klikk."

**What to watch for:**
- Does the tester know the difference between a tenant and a lease (some platforms conflate these)?
- Is the path to tenant creation intuitive from the main nav?
- Does the tester look for tenant creation inside the property or in a separate section?

**Task passes when:** Sarah Botha appears as a tenant in the system.

---

### Scenario 4 — Draft a lease

**Read to tester:**
> "Sarah Botha will move into the unit at 14 Oak Avenue on 1 June. Rent is R9 500 per month. Create a lease for her."

**What to watch for:**
- Does the tester know where to start a lease? (From the unit? From the tenant? From the main nav?)
- Can the tester select both the property/unit and the tenant without confusion?
- Is rent amount and start date entry straightforward?
- Does the AI clause generation feel scary or helpful?

**Task passes when:** A lease draft exists, linked to the unit and to Sarah Botha, with R9 500 rent and 1 June start date.

---

### Scenario 5 — Send the lease for e-signature

**Read to tester:**
> "The lease looks good. Send it to Sarah Botha to sign."

**What to watch for:**
- Is the "send for signing" action visible after lease creation?
- Does the tester understand what happens after they click send (the tenant receives a link)?
- Is the signing status visible (Pending / Signed)?

**Task passes when:** The lease status shows as pending signature, and the tester can confirm a signing link was dispatched.

---

### Scenario 6 — Log a rent payment

**Read to tester:**
> "Sarah paid her first month's rent of R9 500 via EFT. Record the payment in Klikk."

**What to watch for:**
- Does the tester know where rent payments live?
- Is the payment amount pre-filled from the lease, or does the tester have to type it?
- Is "EFT" a recognised payment method in the UI?
- Does a receipt or confirmation appear after saving?

**Task passes when:** A payment record of R9 500 is visible against Sarah's lease.

---

### Scenario 7 — Create a maintenance ticket

**Read to tester:**
> "Sarah reported that the kitchen tap is dripping. Log a maintenance request."

**What to watch for:**
- Is maintenance creation reachable from the property, from the tenant, or from the main nav — and does the tester find the right path?
- Is the category/trade selection clear?
- Does the tester understand the urgency/priority field?
- Does the tester expect to assign a supplier immediately, or is that a separate step?

**Task passes when:** A maintenance ticket exists for the property, categorised under plumbing (or similar), with status "Open".

---

### Scenario 8 — Review the dashboard

**Read to tester:**
> "Take a minute to look at the main dashboard. Tell me what you see and what you think it is telling you."

**What to watch for:**
- Does the tester understand the metrics shown (occupancy, rent due, open maintenance)?
- Can the tester navigate back to any of the earlier screens from the dashboard?
- Are there any items on the dashboard that cause confusion?

**Task passes when:** Tester completes a verbal walk-through of the dashboard without facilitator prompting.

---

## SUS Questionnaire

Administer immediately after Scenario 8. Give the tester a printed or on-screen copy. Do not read the questions aloud — let the tester complete it alone.

### System Usability Scale (SUS)

For each statement, circle a number from 1 (Strongly disagree) to 5 (Strongly agree):

| # | Statement | 1 | 2 | 3 | 4 | 5 |
|---|-----------|---|---|---|---|---|
| 1 | I think that I would like to use this system frequently. | | | | | |
| 2 | I found the system unnecessarily complex. | | | | | |
| 3 | I thought the system was easy to use. | | | | | |
| 4 | I think that I would need the support of a technical person to be able to use this system. | | | | | |
| 5 | I found the various functions in this system were well integrated. | | | | | |
| 6 | I thought there was too much inconsistency in this system. | | | | | |
| 7 | I would imagine that most people would learn to use this system very quickly. | | | | | |
| 8 | I found the system very cumbersome to use. | | | | | |
| 9 | I felt very confident using the system. | | | | | |
| 10 | I needed to learn a lot of things before I could get going with this system. | | | | | |

**Scoring formula:**
- Odd items (1, 3, 5, 7, 9): score = answer − 1
- Even items (2, 4, 6, 8, 10): score = 5 − answer
- Total SUS = sum of all 10 converted scores × 2.5

**Interpretation:**
- 85–100: Excellent
- 72–84: Good
- 52–71: OK — investigate friction points
- 35–51: Poor — significant redesign needed
- Below 35: Awful — major rework required
- Below 68: Usability problem threshold — do not outreach new testers until resolved

---

## Observer note template

```
Session date: ____________  Tester code: ____________  SUS score: ______

| Timestamp | Scenario # | Screen / Component       | Observation                                          | Severity (H/M/L) |
|-----------|------------|--------------------------|------------------------------------------------------|-----------------|
| 00:00:00  |            |                          |                                                      |                 |
```

Severity guide:
- **H** — tester failed the task, rage-clicked, or expressed frustration
- **M** — tester hesitated >15 s, made an error and recovered, or verbally questioned the UI
- **L** — minor verbal comment, slight pause, cosmetic confusion

---

## Findings file template

After the session, save findings to `marketing/ux/uat-findings-YYYY-MM-DD.md` using this structure:

```markdown
---
session_date: YYYY-MM-DD
tester_code: T1
sus_score: 00
---

## Finding UAT-1

- **Scenario:** 1 — Add a property
- **Screen / Component:** Add Property form
- **Observation:** Tester looked for a "Save" button for 20 s; button was labelled "Create"
- **Clarity timestamp:** 00:02:14
- **SUS impact:** yes
- **Severity:** M
- **Suggested fix:** Relabel "Create" to "Save property"
```

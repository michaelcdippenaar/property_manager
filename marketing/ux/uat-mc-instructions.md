# UAT Session Instructions — MC (Facilitator)

**Related task:** UX-006 — First-tester UAT harness: session replay + scenario protocol
**Referenced documents:** `uat-protocol-v1.md`, `uat-consent-form.md`, `uat-runbook.md` (all produced by UX-006)
**Tester:** MC's wife (first tester before Irma Knipe Properties outreach)

---

## Before the Session

### 1. Staging environment

- Confirm staging is up and healthy: open the staging URL in a browser and verify the dashboard loads.
- Confirm `VITE_ENABLE_CLARITY=true` is set in the staging environment. If you need to check, it is documented in `admin/.env.staging.example`. Clarity must be active so session replays are captured during the run.
- Open Clarity (clarity.microsoft.com) and confirm the project is connected to the staging site. You should see your own earlier visits in the recordings list.

### 2. Test data

Load the following before the tester sits down — this prevents dead time during the session:

| Item | Required state |
|------|----------------|
| Staging account | A fresh agent-role account registered and email-verified |
| Property | None yet (tester will add the first one) |
| Unit | None yet (tester will add it) |
| Tenant profile | None yet |
| Lease template | At least one template available in the lease builder |
| E-sign flow | Native signing working on staging (Gotenberg + signer_role public links) |
| Maintenance categories | At least "Plumbing", "Electrical", "General" seeded |

If anything in the above list is missing, fix it before the session — do not ask the tester to work around gaps.

### 3. Consent form

Print or email `marketing/ux/uat-consent-form.md` (produced by UX-006). The tester must sign it before the session begins. File the signed copy. The POPIA consent banner inside the app will appear on first load — the tester clicks Accept before starting scenarios.

### 4. Facilitator setup

- Open a plain text file or notebook to the observer note template (see During the Session below).
- Silence your phone.
- Have a glass of water ready for the tester.
- Do not open any additional browser tabs that might distract or tip off what features exist.

---

## During the Session

### Facilitator framing script (read this aloud before starting)

> "Thank you for helping us test Klikk today. We are testing the software, not you — there are no wrong answers and no wrong moves. If something is confusing, that is exactly the information we need.
>
> Please think aloud as you work: say what you see, what you expect to happen, what you are looking for. If you fall silent I will gently remind you.
>
> I will not help you — even if you are stuck. That silence is deliberate. You can stop or skip a task at any time by saying 'skip'.
>
> The session is 30 minutes. We are recording your screen to help us review later. Any personal data you enter is test data only and will be deleted after the session."

### Think-aloud prompts (use sparingly, only when tester goes silent for >15 seconds)

- "What are you thinking right now?"
- "What are you looking for on the screen?"
- "What did you expect to happen there?"
- "How does this compare to what you expected?"

Do NOT say:
- "Click that button" or any directional instruction
- "Good job" or "You're doing great" (positive reinforcement changes behaviour)
- "Almost there" (reveals proximity to success)
- "That's a known issue" (preempts authentic reaction)

### Silence-is-gold rule

Extended silence from the tester is data. A tester who pauses for 30 seconds on a screen is telling you that screen is confusing. Do not fill the silence. Note the timestamp and the screen they were on. Only use a think-aloud prompt if silence exceeds 15 seconds.

### Scenario protocol (6–10 tasks, ~30 minutes)

Work through these in order, as defined in `marketing/ux/uat-protocol-v1.md`. Do not skip scenarios unless the tester explicitly says "skip" or a hard blocker prevents continuation.

| # | Scenario | Goal verified |
|---|----------|---------------|
| 1 | Add a property | Property creation flow |
| 2 | Add a unit to that property | Unit management flow |
| 3 | Onboard a tenant | Tenant profile creation |
| 4 | Draft a lease for the unit and tenant | Lease builder |
| 5 | Send the lease for e-signature | E-sign send flow |
| 6 | Log a first rental payment | Payment recording |
| 7 | Create a maintenance ticket | Maintenance flow |
| 8 | Review the dashboard | Dashboard readability and navigation |

For scenario wording and task cards, refer to `marketing/ux/uat-protocol-v1.md`.

### Observer note template

Use one row per observation. Record in real time — do not reconstruct from memory afterward.

```
| Timestamp | Scenario # | Screen / Component | Observation | Severity (H/M/L) |
|-----------|------------|--------------------|-------------|-----------------|
| 00:02:14  | 1          | Add Property form  | Tester looked for "Save" button for 20s; it was labelled "Create" | M |
```

Severity guide:
- **H** — tester failed the task, rage-clicked, or expressed frustration
- **M** — tester hesitated >15s, made an error and recovered, or verbally questioned the UI
- **L** — minor verbal comment, slight pause, cosmetic confusion

---

## After the Session

### 1. SUS questionnaire

Immediately after the last scenario, hand the tester the SUS questionnaire (link or printed copy from `uat-protocol-v1.md`). The 10 questions take under 3 minutes. Do not coach answers — leave the tester alone with the form.

Score the SUS per standard formula (odd items: score − 1; even items: 5 − score; sum × 2.5). A score below 68 indicates significant usability problems.

### 2. Debrief (5 minutes, optional)

Ask one open question: "Is there anything you want to tell us about your experience that the form didn't capture?" Take notes. Do not defend design decisions.

### 3. Review Clarity recording (within 24 hours)

- Open Clarity, find the session recorded during the UAT run (filter by the tester's approximate session time).
- Correlate the replay timestamps against your observer notes.
- Note rage-click heatmaps, dead clicks, and scroll depth on each scenario screen.

### 4. Log findings

Create a findings file: `marketing/ux/uat-findings-<YYYY-MM-DD>.md`

Use this structure for each finding:

```markdown
## Finding UAT-<n>

- **Scenario:** <number and name>
- **Screen / Component:** <where it happened>
- **Observation:** <what you saw or heard>
- **Clarity timestamp:** <HH:MM:SS in the recording>
- **SUS impact:** <yes/no — did it likely drag the score?>
- **Severity:** H / M / L
- **Suggested fix:** <optional — do not over-specify>
```

### 5. Hand off to Claude

Once `marketing/ux/uat-findings-<date>.md` is saved and committed, Claude (the autopilot agent) will monitor for the file and promote each finding into a tracked Asana task per the severity rules described in `uat-claude-instructions.md`. You do not need to triage the findings yourself — Claude will post a summary comment on the UX-006 Asana task (GID `1214235754892103`) once triage is complete.

# UAT Session Run-Book — Facilitator Guide

**Session length:** 30 minutes + 5 minutes debrief
**Format:** In-person or screen-share (staging URL shared to tester's browser)
**Documents needed:** `uat-consent-form.md` (printed or digital), `uat-protocol-v1.md` (facilitator copy only)

---

## T-30 minutes: Setup

1. **Stage the environment.**
   - Open the staging URL. Confirm the dashboard loads.
   - Log out. The tester will log in with the prepared fresh account.
   - Confirm `VITE_ENABLE_CLARITY=true` in staging. The consent banner must appear on first load.

2. **Seed test data** (do this yourself before the tester arrives):
   - Fresh agent-role account with email-verified status
   - No existing properties, units, or tenants
   - At least one lease template in the system
   - Maintenance categories: "Plumbing", "Electrical", "General"

3. **Prepare observer notes.**
   - Open a blank text file, the observer note template from `uat-protocol-v1.md`, and a timer.
   - If recording audio, start the recorder now (with tester's knowledge).

4. **Print or open the consent form** (`uat-consent-form.md`). Have a pen ready.

---

## T-0: Tester arrives

### Step 1 — Consent (3 minutes)

Hand the consent form to the tester. Say:

> "Before we start, please read this form. It explains what we are recording and your rights. Take your time."

Answer factual questions about data retention. Do not explain the app yet. Once signed, file the form.

---

### Step 2 — Framing script (2 minutes)

Read this aloud before opening the app:

> "Thank you for helping us test Klikk today. We are testing the software, not you. There are no wrong answers and no wrong moves. If something is confusing, that is exactly the information we need.
>
> Please think aloud as you work: say what you see, what you expect to happen, what you are looking for. If you fall silent I will gently remind you.
>
> I will not help you — even if you are stuck. That silence is deliberate. You can stop or skip a task at any time by saying 'skip'.
>
> The session is 30 minutes. We are recording your screen. Any personal data you enter is test data only and will be deleted after the session. Do you have any questions before we begin?"

Pause for questions. Answer only factual questions. Then open the staging URL in the tester's browser.

---

### Step 3 — Consent banner (1 minute)

The Clarity consent banner will appear at the bottom of the screen.

Do not prompt the tester. Watch whether they:
- Notice the banner
- Read it
- Click Accept or Decline

Note the outcome in your observer notes. The tester's choice is valid either way — do not nudge.

---

### Step 4 — Run scenarios (22 minutes)

Work through Scenarios 1–8 from `uat-protocol-v1.md` in order.

**To introduce each scenario:** read the task card aloud, then stop talking.

**Silence rule:** If the tester goes silent for more than 15 seconds, use one of these prompts — and only one per silence:
- "What are you thinking right now?"
- "What are you looking for on the screen?"
- "What did you expect to happen there?"

**Do NOT say:**
- "Click that button"
- "Good job" or "You're doing great"
- "Almost there"
- "That's a known issue"

**If the tester is completely stuck for more than 2 minutes and cannot proceed:** note the failure, say "Let's move on to the next task" and continue. Do not solve the task for them.

**Timing guide (approximate):**

| Scenario | Target time |
|----------|-------------|
| 1 — Add property | 3 min |
| 2 — Add unit | 2 min |
| 3 — Add tenant | 2 min |
| 4 — Draft lease | 5 min |
| 5 — Send for e-sign | 2 min |
| 6 — Log payment | 3 min |
| 7 — Maintenance ticket | 3 min |
| 8 — Dashboard review | 2 min |
| **Total** | **22 min** |

If ahead of time, let the tester explore freely within the current scenario. If behind, note which scenarios were cut.

---

### Step 5 — SUS questionnaire (3 minutes)

After the final scenario, say:

> "We have one last thing — a short questionnaire. It takes about three minutes. Please complete it on your own. I will step back."

Hand or screen-share the SUS questionnaire from `uat-protocol-v1.md`. Leave the tester alone with it.

Score immediately after they return it (odd items: score − 1; even items: 5 − score; sum × 2.5).

---

### Step 6 — Debrief (5 minutes, optional)

Ask only:

> "Is there anything you want to tell us about your experience that the form did not capture?"

Take notes. Do not defend design choices. Thank the tester.

---

## After the session

### Within 2 hours

1. Transcribe observer notes into the findings file format (template in `uat-protocol-v1.md`).
2. Record SUS score at the top of the findings file.
3. Save the file as `marketing/ux/uat-findings-YYYY-MM-DD.md` and commit.

### Within 24 hours

1. Open Microsoft Clarity and find the session recording (filter by approximate session time).
2. Correlate Clarity timestamps with observer notes.
3. Note rage clicks, dead clicks, and scroll-depth anomalies.
4. Add any additional findings from the Clarity replay to the findings file.

### Hand off

Once `marketing/ux/uat-findings-YYYY-MM-DD.md` is committed, Claude (the autopilot agent) picks it up automatically and converts findings into tracked Asana tasks per the rules in `uat-claude-instructions.md`. You do not need to triage manually.

---

## Quick reference: what to do if things go wrong

| Problem | Response |
|---------|----------|
| Staging is down | Postpone. Never run the session on dev or production. |
| Tester can't log in | Fix auth before the session — not during. |
| Clarity banner doesn't appear | Note it, continue the session. Clarity can be checked manually later. |
| Tester enters real personal data | Reassure them, note the fields affected, delete data from staging after the session. |
| Tester becomes distressed or uncomfortable | Stop the session immediately. Thank them. Do not pressure continuation. |
| Session runs over 35 minutes | Cut remaining scenarios. A partial session is better than a rushed one. |

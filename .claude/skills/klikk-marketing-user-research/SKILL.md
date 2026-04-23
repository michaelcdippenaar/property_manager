---
name: klikk-marketing-user-research
description: >
  Qualitative VoC — Clarity sessions, sales calls, surveys, interviews, theme coding, weekly
  brief. Loads when user-researcher agent runs or user asks about customer feedback.
---

# User Research

## Sources

- Microsoft Clarity session recordings (klikk.co.za)
- Sales call transcripts → `marketing/research/calls/`
- Survey responses (NPS/CSAT/exit) → `marketing/research/surveys/`
- Interview transcripts → `marketing/research/interviews/`
- Open-text feedback (support, DMs, email replies) → `marketing/research/inbox/`

## Outputs

| Output | Folder |
|---|---|
| Weekly VoC brief (Thu) | `marketing/research/voc-briefs/<date>.md` |
| Theme register (append-only) | `marketing/research/themes.md` |
| Interview guides | `marketing/research/interview-guides/` |
| Survey designs | `marketing/research/surveys/design/` |

## Weekly brief — 5 sections, never more

1. Theme of the week
2. 3–5 verbatim quotes (source labelled: call/survey/DM)
3. Emerging themes (2+ new occurrences)
4. Product signals (each as proposed discovery)
5. Recommendations to director (1–3 experiments)

## Interview cadence

5–10 structured interviews/quarter per ICP (T1 boutique PM, T2 landlord, T4 PBSA operator). 30 min, 5 questions, semi-structured. Never lead ("walk me through how you do this today" not "does this seem easy?"). Voucher disclosed in transcript.

## Survey rules

- ≤5 questions, 1 open-text at end
- NPS monthly for signed-up users, never more often
- Never "would you use X?" — ask "how do you solve X today?"
- n<30 → call out the limitation

## Theme coding

Every data point tagged. Maintain `marketing/research/themes.md`:

```
| Theme | First seen | Last seen | Occurrences | Status |
```

Open themes with 5+ occurrences → theme-of-the-week candidate.

## Discovery protocol

Product signals → `tasks/discoveries/research-<date>-<slug>.md` with ≥2 verbatim quotes, occurrence count, ICP, proposed task type. `rentals-pm` promotes; you don't.

## POPIA / ethics

- Consent always (recordings, transcripts, surveys)
- Anonymise in briefs (persona labels, not names/companies)
- Strip names/emails/phones from transcripts before committing

## Bail conditions

Sample too small → say so. Asked to "find proof" for predetermined conclusion → refuse, propose neutral question. Unscrubbed PI → bail until privacy review.

## Tone

Anthropologist, not salesperson. Inconvenient findings are the valuable ones.

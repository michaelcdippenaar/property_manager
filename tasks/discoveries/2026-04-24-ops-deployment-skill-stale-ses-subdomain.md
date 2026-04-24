---
discovered_by: rentals-reviewer
discovered_during: OPS-006
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: OPS
---

## What I found
`.claude/skills/klikk-ops-deployment/SKILL.md` still documents the old `mail.klikk.co.za` SES isolated-subdomain design in multiple places (lines 9, 16, 43, 108, 119, 121, 125, 127, 133–135). DEC-023 (2026-04-24) superseded that design: SES sends from the apex `klikk.co.za` with SPF extended to include amazonses.com, DKIM CNAMEs on the apex, and a single DMARC record covering both Google Workspace and SES.

## Why it matters
The skill is invoked for deployment/ops work. If another agent picks it up it will re-publish conflicting DNS guidance (isolated SPF/DKIM/DMARC on `mail.klikk.co.za`) that contradicts `docs/ops/email-deliverability.md` and `docs/ops/dns.md`. No production impact today — records haven't been created — but a time-bomb for the next person who runs this skill.

## Where I saw it
- `.claude/skills/klikk-ops-deployment/SKILL.md:9,16,43,108–135`

## Suggested acceptance criteria (rough)
- [ ] Rewrite the email section of `klikk-ops-deployment/SKILL.md` to match DEC-023 (apex sender, dual-sender coexistence, single DMARC on apex)
- [ ] Update the subdomain table (line 43) to drop `mail.klikk.co.za`
- [ ] Cross-reference `docs/ops/email-deliverability.md` as the canonical runbook

## Why I didn't fix it in the current task
Skill file is outside OPS-006's `Files likely touched` scope. PM should decide whether this is a solo micro-task or bundled into the next ops skill refresh.

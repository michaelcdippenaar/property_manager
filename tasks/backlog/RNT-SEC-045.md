---
id: RNT-SEC-045
stream: rentals-sec
title: "Remove hardcoded prod credentials from agent-app LoginPage dev block + rotate password if still live"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214241211323911"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Remove hardcoded real credentials (`mc@tremly.com` / `Number55dip`) from the `import.meta.env.DEV` pre-fill block in `agent-app/src/pages/LoginPage.vue`, replace with env-var sourcing or remove entirely, and confirm the exposed password has been rotated in staging and production before code fix lands.

## URGENT — action required before code fix

**MC must rotate the password for `mc@tremly.com` on staging and production immediately.** The credential pair `mc@tremly.com` / `Number55dip` appears in the git history and is visible to anyone who clones this repo. Do not wait for the code change — rotate the password now and confirm here in the Asana task notes.

## Acceptance criteria
- [ ] **Password rotated (pre-code):** MC confirms in Asana comments that the password for `mc@tremly.com` has been changed in staging and production before any implementer touches this task.
- [ ] Hard-coded email (`mc@tremly.com`) and password (`Number55dip`) removed from `agent-app/src/pages/LoginPage.vue` lines 119, 120, 129.
- [ ] If dev-mode pre-fill is still desired, source credentials from `.env.development` env vars (`DEV_LOGIN_EMAIL` / `DEV_LOGIN_PASSWORD`) — document in `.env.development.example` with empty default values and a comment warning never to commit real credentials.
- [ ] Same audit applied to equivalent LoginPage files in `admin/` and `web_app/` — no hardcoded real credentials in any DEV block.
- [ ] `git log --all -S 'Number55dip'` returns no results in the clean working tree post-fix (note: history rewrite is out of scope for v1 but should be tracked).
- [ ] Consider adding a pre-commit hook or CI grep step that blocks committing strings matching known credential patterns.

## Files likely touched
- `agent-app/src/pages/LoginPage.vue` (lines 119, 120, 129)
- `agent-app/.env.development.example` (create / update)
- `admin/src/pages/LoginPage.vue` (audit)
- `web_app/src/pages/LoginPage.vue` (audit)

## Test plan
**Manual:**
- Start agent-app in dev mode (`import.meta.env.DEV === true`); confirm login form fields are empty (or populated from env vars if configured) — no hardcoded email or password.
- Start agent-app in production build; confirm same.

**Automated:**
- `grep -r 'Number55dip' agent-app/src admin/src web_app/src` — must return zero results.
- `grep -r 'mc@tremly.com' agent-app/src admin/src web_app/src` — must return zero results in Vue source files.

## Handoff notes
2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-agent-app-hardcoded-dev-credentials.md` (found by rentals-reviewer during RNT-010). Priority elevated to P0 — potential live production password visible in repo history. MC must rotate password immediately regardless of code fix timeline.

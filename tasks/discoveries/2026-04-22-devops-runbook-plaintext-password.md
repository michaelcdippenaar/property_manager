---
discovered_by: rentals-reviewer
discovered_during: OPS-012
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: OPS
---

## What I found
`deploy/DEVOPS.md` contains `# password: pass` inline in SSH example commands at lines 19 and 276. This is the actual staging server password documented in a committed, public-facing runbook.

## Why it matters
The staging server (`102.135.240.222`) is now publicly reachable from the internet (confirmed by OPS-012). Previously this credential leak was low-risk because the IP was a private LAN address. It is now directly exploitable: anyone with repo access (or a public repo) can SSH into the staging server with the documented username and password.

## Where I saw it
- `deploy/DEVOPS.md:19` — `ssh mc@102.135.240.222    # password: pass`
- `deploy/DEVOPS.md:276` — `ssh mc@102.135.240.222       # password: pass`

## Suggested acceptance criteria (rough)
- [ ] Remove the inline password comment from all SSH examples in DEVOPS.md
- [ ] Rotate the staging server SSH password
- [ ] Disable password-based SSH auth on the staging server (`PasswordAuthentication no` in `/etc/ssh/sshd_config`) — key-based auth only (the deploy key from OPS-012 §5a satisfies this for CI; MC should add their personal key too)

## Why I didn't fix it in the current task
Out of scope for OPS-012 (which only updates the IP); rotating credentials and disabling password auth requires server-side action and a coordinated DEVOPS.md cleanup that deserves its own tracked task.

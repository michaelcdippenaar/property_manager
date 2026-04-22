---
discovered_by: rentals-implementer
discovered_during: OPS-001
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: OPS
---

## What I found

The staging server is on a private LAN (`192.168.1.235`). GitHub Actions runners cannot reach it directly, so the SSH deploy step in `staging-deploy.yml` will fail with a connection timeout unless a tunnel or public-facing access is set up first.

## Why it matters

The entire staging-deploy workflow becomes a no-op until this is resolved. CI will pass (it doesn't need the server), but the deploy job will always time out, making the pipeline incomplete and giving a false sense of automation.

## Where I saw it

- `deploy/DEVOPS.md` — staging IP listed as `192.168.1.235`
- `.github/workflows/staging-deploy.yml` — `ssh-keyscan -H ${{ secrets.STAGING_HOST }}` will time out on a private address

## Suggested acceptance criteria (rough)
- [ ] Staging server reachable from a public IP or via a secure tunnel (options: port-forward on the home router with firewall rules; Cloudflare Tunnel; Tailscale; move to a cloud VM)
- [ ] `STAGING_HOST` secret set to the reachable address
- [ ] Staging deploy workflow runs end-to-end without timeout
- [ ] SSH access locked to GitHub Actions IP range or to a dedicated key only

## Why I didn't fix it in the current task

It requires an infrastructure decision (router port-forward vs. VPN tunnel vs. cloud server migration) that is above the implementer's scope and may drive a larger ops decision about the staging environment.

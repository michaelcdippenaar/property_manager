---
discovered_by: ux-onboarding
discovered_during: UX-002
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: UX
---

## What I found
Both `invite_tenant.md` and `welcome_tenant.md` emails are one-sentence bodies with no context about what Klikk is, what the tenant should expect, or what happens if the invite link does not work. The invite email does not mention the 72-hour expiry in the body — only in a `note` frontmatter field. The welcome email's CTA says "View your lease" but at the time of sending the lease may not yet be signed.

## Why it matters
A new tenant receiving the invite email has no existing relationship with the Klikk brand. Thin copy increases the chance that they dismiss it as spam, miss the expiry window, or are confused when the CTA leads to an empty lease screen. Higher invite abandonment = more agent time re-sending and explaining.

## Where I saw it
- `content/emails/invite_tenant.md` — one sentence body; 72h expiry not in body; no "what is Klikk" context
- `content/emails/welcome_tenant.md` — CTA "View your lease" sent immediately after account creation, before signing

## Suggested acceptance criteria (rough)
- [ ] Invite email body: 3–4 sentences explaining Klikk in plain language, what to do when the link is clicked, and that the link expires in 72 hours
- [ ] Welcome email CTA updated to "Go to your portal" (lease may be pending)
- [ ] Both emails pass a Flesch-Kincaid Grade 8 readability check

## Why I didn't fix it in the current task
Email copy changes should go through GTM review. Out of scope for the UX code audit.

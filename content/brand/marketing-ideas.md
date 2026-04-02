# Klikk Marketing Ideas

A running list of marketing angles, copy hooks, and campaign ideas.
Add ideas here as they come up — refine and activate them in the relevant copy files.

---

## Idea: Track the Full Tenant Lifecycle

**Core angle:** Most property management tools focus on one slice — payments, or leases, or maintenance. Klikk is the only platform that tracks a tenant from first inquiry all the way through to deposit refund.

**Hook lines:**
- "Know exactly where every tenant is in their journey — at a glance."
- "From first viewing to final refund. Every stage tracked. Nothing falls through the cracks."
- "Your tenant signed last month. When does their lease expire? When was the last maintenance request? What's outstanding on their account? Klikk knows."

**Target audience:** Agents managing 10+ tenants who lose track of where each one is in the lifecycle (renewal coming up, notice period started, inspection due).

**Suggested placement:** Homepage lifecycle section headline, demo flow step 1, LinkedIn content.

**Activation status:** Idea — not yet in website copy

---

## Idea: Tenant Information Automatically Uploaded to Database

**Core angle:** Eliminate manual data capture. When a new tenant applies, their personal details, ID documents, employment details, and references are captured once — and flow automatically into the Klikk database. No re-keying, no spreadsheets, no lost paperwork.

**Hook lines:**
- "Tenant applies online. Their details are already in your system."
- "Stop re-typing information that tenants already gave you."
- "One form. Zero manual data entry. Every detail captured, verified, and stored."
- "From application to lease — Klikk pre-fills everything your tenant already told you."

**Target audience:** Agents frustrated by manual onboarding (capturing ID numbers, banking details, employer info by hand).

**Messaging nuance:** Emphasise POPIA compliance — data is collected with consent, stored securely, SA-hosted. This turns a potential concern (AI storing personal data) into a differentiator.

**Suggested placement:** Tenant onboarding feature description, "How it works" section, objection handling for "We're worried about data security".

**Activation status:** Idea — not yet in website copy

---

## Idea: Upload Old Contracts — Property + Tenant Created Automatically

**Core angle:** Switching property management software is painful because of migration. Klikk eliminates the biggest barrier: instead of manually capturing every existing property and tenant, you just upload your old lease PDFs/Word docs. Klikk's AI reads them and automatically creates the property record, the tenant record, and the lease — populated with the correct details.

**Hook lines:**
- "Already have tenants? Upload your old contracts. Klikk does the rest."
- "Migrate your entire portfolio in minutes — not weeks."
- "Drop in your existing leases. We'll create the properties, add the tenants, and have you live before lunch."
- "Don't start from scratch. Your old contracts are your import file."
- "Switching to Klikk? Upload your leases. We'll handle onboarding your whole portfolio automatically."

**Target audience:** Agents or landlords switching from another system (or from spreadsheets/paper) who are deterred by the effort of re-entering all existing data. This directly removes the #1 adoption blocker.

**Why this is a big deal:** Every competitor requires manual data entry to migrate. This makes Klikk the only platform where migration is effortless. It's a direct objection-killer for "I have 30 existing tenants, it'll take months to set up."

**Messaging nuance:**
- Lean into the AI angle: "Our AI reads the lease and extracts every detail — tenant name, ID number, monthly rental, escalation clause, expiry date."
- Tie to POPIA: extracted data stored securely with SA-hosted infrastructure.
- Pair with the "automatically uploaded to database" idea above — these are two sides of the same story (new tenants captured from application forms, existing tenants imported from contracts).

**Suggested placement:**
- Homepage "How it works" or onboarding section
- Migration/switching landing page
- Demo flow: show live contract upload → auto-populated property and tenant cards
- Key objection rebuttal: "We already have tenants, it'll take too long to set up"

**Activation status:** Idea — not yet in website copy. Consider making this a featured homepage callout — it's a strong differentiator.

---

## Idea: Product Video (OpenArt.ai)

**Core angle:** A short product video (60–90 seconds) showing the platform in action removes friction for visitors who won't read feature descriptions. Video converts better than text for SaaS demos.

**Video concept:** Walk through the core "wow moments":
1. AI generates a lease in under 3 minutes (show the chat + lease appearing)
2. Tenant signs from their phone (e-signing flow)
3. Maintenance ticket raised on tenant app → AI triages → supplier dispatched
4. Owner sees it all update in real-time on their dashboard

**Technical notes:**
- Created with OpenArt.ai
- Embed on the homepage hero — wire up the "Watch Demo" button (currently `href="#"`)
- Also embed on `/pricing` page above the tiers (video just before pricing = highest converting placement)
- Host on YouTube (unlisted) or Vimeo — embed via iframe or lightweight facade (click-to-load to avoid performance hit)

**Homepage integration:** Replace `href="#"` on the "Watch Demo" button with either:
- A YouTube/Vimeo URL that opens in a modal lightbox
- Or a `/demo` page with the video + a "Start Free" CTA below it

**Activation status:** Video to be created. Once URL is available, update Hero.astro Watch Demo href.

---

## How to activate an idea

1. Refine the hook line for the target channel
2. Update the relevant copy file in `content/website/copy/`
3. If it becomes a homepage section, update `content/product/features.yaml` with `show_on_homepage: true`
4. Tag with the marketing channel (paid, organic, LinkedIn, demo)
5. For video: update `href="#"` on Watch Demo button in `website/src/components/Hero.astro`

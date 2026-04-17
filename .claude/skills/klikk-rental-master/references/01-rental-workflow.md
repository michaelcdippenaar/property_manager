# SA Residential Rental Workflow — Full Lifecycle

The complete rental lifecycle covering all 15 stages across 4 phases. The lifecycle is **circular** — the end of one tenancy feeds directly into the start of the next. A new tenancy cannot begin until the previous one is fully closed out.

**Key principles:**
- The lifecycle is driven by the **notice period** (typically 2 months). Marketing starts the day notice is confirmed.
- Stages 1–7 happen **while the previous tenant still occupies** the property.
- The turnaround window (stages 8–11) is **overnight** — move-out inspection in the afternoon, repairs overnight, move-in inspection the next morning.
- The goal is to **compress vacancy to zero days** by overlapping pre-tenancy stages with the outgoing notice period.

**Example timeline (1 Dec → 30 Nov contract):**
- Notice given: ~1 Oct
- Marketing, viewings, screening: Oct
- Lease signed, invoicing set up, deposit paid: Oct–Nov
- Move-out inspection: 30 Nov afternoon
- Repairs & cleaning: 30 Nov evening → 1 Dec early morning
- Move-in inspection + onboarding: 1 Dec morning

---

## Phase A: Pre-Tenancy (~2 months, during notice period)

### Stage 1: Notice Given

- **Who**: Tenant or landlord (either party)
- **Trigger**: Decision to vacate or not renew — this stage kicks off the entire cycle
- **Actions**: Issue 2-month written notice (or as per lease terms)
- **Notice periods**:

| Scenario | Notice period | Legal basis |
|---|---|---|
| Month-to-month (either party) | Minimum 1 calendar month written notice | RHA s5(5) |
| Fixed-term (tenant cancels early) | 20 business days | CPA s14 |
| Fixed-term (landlord cancels early) | Breach notice → reasonable time to remedy | RHA s5(3)(c) |
| Breach by tenant | 20 business days written notice to remedy | CPA / common law |

- **Delivery**: Written notice via email, registered post, or hand delivery (keep proof)
- **Documents**: Written termination notice with delivery proof
- **Legal basis**: RHA s5(5), CPA s14
- **Pitfall**: Verbal notice is not enforceable — always put it in writing with a delivery record
- **Klikk note**: Notice date = marketing start date. The agent dashboard should immediately surface "Publish Listing" as the next action.

### Stage 2: Marketing & Listing

- **Who**: Landlord or estate agent (with signed mandate agreement)
- **When**: Immediately after notice is confirmed
- **Occupancy**: Previous tenant still in the property
- **Actions**: Professional photos, property description, rental price, listing on portals (Property24, Private Property, social media)
- **Documents**: Mandate agreement (if using agent), compliance certificates (CoC electrical, gas, electric fence)
- **Legal basis**: Property Practitioners Act 22/2019 — agent must hold valid Fidelity Fund Certificate
- **Pitfall**: Advertising without FFC is unlawful; agent cannot charge commission without one

### Stage 3: Viewings

- **Who**: Agent or landlord shows the property; prospective tenants tour
- **When**: During the notice period, while previous tenant still occupies
- **Occupancy**: Previous tenant still in the property (must cooperate with reasonable viewing requests)
- **Actions**:
  1. Schedule viewing appointments (individual or open house)
  2. Present the property — point out features, house rules, utilities setup
  3. Collect interest / pre-qualification info
  4. Follow up with promising applicants to proceed to formal application
- **Legal basis**: Property Practitioners Act 22/2019 — agent conducting viewings must hold valid FFC
- **POPIA note**: Contact details collected at viewings must be handled per POPIA (consent, purpose limitation)
- **Pitfall**: Discrimination during viewings (refusing to show based on race, religion, gender, etc.) is prohibited under RHA s4A — keep a viewing record to demonstrate fair access

### Stage 4: Tenant Screening

- **Who**: Landlord or managing agent
- **When**: After viewings, while previous tenant still occupies
- **Occupancy**: Previous tenant still in the property
- **Actions**:
  1. Collect application form with consent for checks
  2. Credit check (TransUnion, Experian, XDS) — assess payment history and affordability
  3. Employment verification — 3 months payslips, bank statements, employment letter
  4. Previous landlord references — rental payment history, property condition
  5. Criminal record check (with written POPIA consent)
  6. FICA verification — ID against Home Affairs database
- **Rule of thumb**: Tenant gross income should be ≥ 3× monthly rent
- **Legal basis**: POPIA — must have written consent for all checks; RHA s4A — may not unreasonably refuse tenancy (no discrimination)
- **Documents**: Application form, POPIA consent form, FICA documents (ID + proof of address)
- **Pitfall**: Refusing a tenant without lawful grounds may constitute an unfair practice under RHA s4A

### Stage 5: Lease Execution

- **Who**: Landlord, tenant(s), witnesses
- **When**: After screening passes; before move-out day of previous tenant
- **Occupancy**: Previous tenant still in the property
- **Actions**:
  1. Draft lease agreement (see `lease-rental-agreement` skill for generation)
  2. Both parties review and negotiate terms
  3. Sign lease via e-signing — each party retains a copy
  4. Attach house rules as annexure (mandatory per RHA s5(5))
- **Legal basis**: RHA s5(2) — tenant has right to a written lease; CPA s22 — must be in plain language
- **Documents**: Signed lease agreement, house rules annexure, FICA copies retained
- **Pitfall**: Verbal leases are valid but hard to enforce — always provide a written lease

### Stage 6: Recurring Invoice Setup

- **Who**: Managing agent or landlord
- **When**: At lease execution or shortly after
- **Occupancy**: Previous tenant still in the property
- **Actions**:
  1. Configure monthly rent schedule (start date, end date, escalation %)
  2. Set up payment method — EFT details or debit order (requires POPIA consent)
  3. Configure invoice delivery (email, tenant portal, or both)
  4. Set up late payment reminders and escalation rules
- **Payment methods**: EFT (preferred — clear audit trail), debit order (requires POPIA consent), cash (issue receipt)
- **Legal basis**: Lease terms; RHA s5B — tenant must pay on time; RHA s5A — receipts on request
- **Pitfall**: Landlord may NOT cut utilities or change locks for non-payment — must follow legal process

### Stage 7: Deposit Payment

- **Who**: New tenant pays; landlord/agent lodges
- **When**: After lease is signed, before move-in
- **Occupancy**: Previous tenant still in the property
- **Actions**:
  1. Receive deposit (max 2× monthly rent per RHA regulations) + first month's rent
  2. Place deposit in interest-bearing account (rate ≥ standard savings account)
  3. Provide tenant with deposit receipt including bank details
- **Interest accrual**: Interest accrues from the day the deposit is **lodged in the account**, NOT from the lease start date. If tenant pays deposit on 15 Nov and landlord lodges on 18 Nov, interest accrues from 18 Nov.
- **Timing**: Landlord must lodge within 3–7 days of receipt
- **Legal basis**: RHA s5(3)(f)–(h)
- **Documents**: Deposit receipt, proof of interest-bearing account
- **Pitfall**: Commingling deposit with personal funds is unlawful; interest belongs to the tenant

---

## Phase B: Turnaround (overnight window — same day to next morning)

This is the critical transition period. Every hour the property is empty = lost rental income.

### Stage 8: Move-Out (Outgoing) Inspection

- **Who**: Landlord/agent AND outgoing tenant — both should attend
- **When**: Last day of lease, afternoon (to maximise overnight repair time)
- **Occupancy**: Previous tenant (last day)
- **Actions**:
  1. Joint walk-through comparing to ingoing inspection report
  2. Identify damage beyond fair wear and tear
  3. Date/time-stamped photographs for comparison
  4. Both parties sign outgoing inspection report
  5. Keys handed over
- **Fair wear and tear examples**: Faded paint, minor scuff marks, worn carpets from normal use
- **Tenant damage examples**: Holes in walls, broken fixtures, cigarette burns, stains requiring professional cleaning
- **Timing**: On the afternoon of the last day of the lease (e.g., 30 Nov PM)
- **Legal basis**: RHA deposit refund provisions
- **Documents**: Signed outgoing inspection report with photos
- **Pitfall**: If tenant does not attend, landlord must inspect within 7 days and has 21 days to refund (not 14)

### Stage 9: Repairs & Cleaning

- **Who**: Contractors, cleaning crews — pre-booked before move-out
- **When**: Overnight (evening of move-out through early morning before move-in)
- **Occupancy**: Nobody — Vacant
- **Actions**:
  1. Contractors work from the snag list generated at move-out inspection
  2. Professional cleaning
  3. Touch-up painting, fixture replacement as needed
  4. Final walk-through by agent/landlord early morning
- **Critical**: Contractors MUST be pre-booked before the move-out inspection — they cannot be arranged after. The snag list from the outgoing inspection drives the overnight work.
- **Timing**: Evening of move-out day → early morning of move-in day
- **Pitfall**: If repairs cannot be completed overnight, the incoming tenant must be informed and an agreement reached about outstanding items

### Stage 10: Move-In (Ingoing) Inspection

- **Who**: Landlord/agent AND new tenant — both must attend
- **When**: Morning of lease start date (e.g., 1 Dec, early AM)
- **Occupancy**: New tenant (first day)
- **Actions**:
  1. Walk through every room and external area
  2. Document condition of walls, floors, ceilings, fixtures, fittings, appliances
  3. Take date/time-stamped photographs and/or video
  4. Record all pre-existing defects (including any outstanding repairs from overnight)
  5. Create inventory list (furnished properties)
  6. Both parties sign the inspection report (3 copies: tenant, landlord, agent)
- **Legal basis**: RHA s5(3) — joint inspection is mandatory
- **Documents**: Signed incoming inspection report with photos, inventory list
- **Pitfall**: If landlord fails to conduct joint inspection, they **lose the right to claim damages from the deposit**

### Stage 11: Onboarding

- **Who**: Agent/landlord + new tenant
- **When**: Same day as move-in inspection (e.g., 1 Dec)
- **Occupancy**: New tenant
- **Actions**:
  1. Hand over keys (all copies — front door, security gate, alarm remote, garage)
  2. Transfer utilities — electricity, water, gas, internet
  3. Provide welcome pack — emergency contacts, municipal office details, body corporate rules
  4. Set up tenant portal access (login credentials, app download)
  5. Confirm emergency maintenance contact numbers
  6. Walk through appliance operation if applicable
  7. Confirm first rent payment date and method
- **Documents**: Key register, utilities transfer forms, welcome pack
- **Pitfall**: Failing to transfer utilities means the previous tenant remains liable — and may dispute charges

---

## Phase C: Active Tenancy (12 months)

### Stage 12: Rent Collection (ambient)

- **Who**: Landlord or managing agent
- **When**: Monthly, on the agreed date (typically 1st of each month)
- **Occupancy**: New tenant
- **Actions**:
  1. Invoices auto-generated from recurring schedule (set up in Stage 6)
  2. Collect rent on the agreed date
  3. Issue receipt on request (RHA s5A)
  4. Send late payment reminder if rent is overdue
  5. Issue formal written notice for persistent non-payment
- **Legal basis**: Lease terms; RHA s5B — tenant must pay on time
- **Pitfall**: Landlord may NOT cut utilities or change locks for non-payment — must follow legal process

### Stage 13: Maintenance (ambient)

- **Who**: Tenant reports → landlord/agent responds → supplier dispatched
- **When**: Throughout the tenancy
- **Occupancy**: New tenant
- **Responsibilities**:
  - **Landlord (RHA s5A)**: Structural repairs, major maintenance, habitability, plumbing/electrical infrastructure
  - **Tenant (RHA s5B)**: Day-to-day cleanliness, minor maintenance, damage caused by negligence
- **Process**: Tenant submits written request → landlord acknowledges → arrange repair within reasonable time
- **Emergency repairs**: Burst pipes, electrical faults, security breaches — immediate response required
- **Pitfall**: Tenant may withhold rent if landlord fails to maintain habitability (but should seek Tribunal guidance first)

### Stage 14: Notice Given (cycle restarts)

- **Who**: Landlord initiates renewal notification; tenant or landlord may give notice
- **When**: 40–80 business days before lease expiry (CPA s14 renewal notification), then 2-month notice period if vacating
- **Occupancy**: Current tenant
- **Actions**:
  1. Landlord notifies tenant 40–80 business days before lease expires (CPA s14)
  2. Offer renewal terms (including any escalation)
  3. Tenant accepts or declines

- **Three paths**:

| Path | What happens |
|---|---|
| **Renew** | New 12-month lease signed, no gap, stays at Stage 12 |
| **Go month-to-month** | Same terms continue, 1-month notice required to end (RHA s5(5)) |
| **Vacate** | 2-month notice given → lifecycle restarts from Stage 1 |

- **Legal basis**: CPA s14 — mandatory renewal notification for fixed-term leases
- **Documents**: Written renewal notice, new lease or addendum (if terms change)
- **Pitfall**: Failing to notify triggers automatic month-to-month continuation — landlord cannot then claim fixed-term breach
- **Klikk note**: For a 1 Dec → 30 Nov contract, the 80 business day notification window is approximately June. The platform should auto-trigger a reminder.

---

## Phase D: Closeout

### Stage 15: Deposit Refund

- **Who**: Landlord/agent
- **When**: After move-out inspection, within statutory timelines
- **Occupancy**: Nobody (or next tenant already in)
- **Timelines**:

| Scenario | Refund deadline |
|---|---|
| No damage, no unpaid amounts | **7 days** after lease termination |
| Damage found, repairs needed | **14 days** after repairs completed (written quotation within 14 days) |
| Tenant absent from inspection | **21 days** from lease expiration |

- **Interest**: All accrued interest (from the day the deposit was lodged in the interest-bearing account) must be paid to the tenant with the refund
- **Lawful deductions**: Damage beyond fair wear and tear (with invoices), unpaid rent, unpaid utilities — must be itemised
- **Dispute**: Either party may refer to the provincial Rental Housing Tribunal (free service, binding ruling)
- **Documents**: Deposit refund statement with itemised deductions, repair invoices/quotations
- **Pitfall**: Deducting without invoices or inspection evidence = Tribunal will rule in tenant's favour

---

## Quick Reference: Document Checklist by Stage

| Stage | Required Documents |
|---|---|
| 1. Notice Given | Written termination notice with delivery proof |
| 2. Marketing & Listing | Mandate agreement, compliance certificates |
| 3. Viewings | Viewing schedule, prospect contact log |
| 4. Tenant Screening | Application form, POPIA consent, FICA docs |
| 5. Lease Execution | Signed lease, house rules annexure |
| 6. Recurring Invoice Setup | Billing schedule, debit order mandate (if applicable) |
| 7. Deposit Payment | Deposit receipt, proof of interest-bearing account |
| 8. Move-Out Inspection | Signed outgoing inspection report + photos |
| 9. Repairs & Cleaning | Snag list, contractor invoices |
| 10. Move-In Inspection | Signed ingoing inspection report + photos, inventory list |
| 11. Onboarding | Key register, utilities transfer, welcome pack |
| 12. Rent Collection | Monthly receipts (on request) |
| 13. Maintenance | Written maintenance requests and records |
| 14. Notice Given (cycle) | CPA s14 renewal notice, or written termination notice |
| 15. Deposit Refund | Deposit refund statement, repair invoices |

---

## Quick Reference: Occupancy by Stage

| Stage | Who Occupies |
|---|---|
| 1–7 (Pre-tenancy) | **Previous Tenant** |
| 8 (Move-Out Inspection) | **Previous Tenant** (last day) |
| 9 (Repairs & Cleaning) | **Nobody — Vacant** |
| 10–11 (Move-In + Onboarding) | **New Tenant** (first day) |
| 12–14 (Active Tenancy) | **New Tenant** |
| 15 (Deposit Refund) | **Nobody** or **Next Tenant** already in |

# Documents and Records in SA Residential Rentals

Every document in the rental lifecycle: what it is, when it's needed, who prepares it, the legal basis, and how long to keep it.

---

## Document Register

Mapped to the 15-stage circular lifecycle (see `01-rental-workflow.md`). Stages 1–7 happen during the previous tenant's notice period. Stages 8–11 are the overnight turnaround. Stages 12–14 are active tenancy. Stage 15 is closeout.

| # | Document | Lifecycle Stage | Prepared by | Legal basis | Retention |
|---|----------|----------------|-------------|-------------|-----------|
| 1 | Written termination notice | Stage 1: Notice Given | Initiating party | RHA s5(3)(c), CPA s14 | 3 years after termination |
| 2 | Mandate agreement | Stage 2: Marketing & Listing | Agent + landlord | PPA 22/2019 | Duration of mandate + 5 years |
| 3 | Compliance certificates | Stage 2: Marketing & Listing | Qualified inspectors | Various regulations | Duration of validity |
| 4 | Viewing schedule / prospect log | Stage 3: Viewings | Agent | Best practice / POPIA | Duration of tenancy + 3 years |
| 5 | FICA documents | Stage 4: Tenant Screening | Tenant provides; agent/landlord verifies | FICA 38/2001 s21 | 5 years after relationship ends |
| 6 | Tenant application form | Stage 4: Tenant Screening | Agent/landlord | Best practice | Duration of tenancy + 3 years |
| 7 | POPIA consent form | Stage 4: Tenant Screening | Agent/landlord | POPIA s11 | Duration of tenancy + 3 years |
| 8 | Credit check report | Stage 4: Tenant Screening | Credit bureau (TransUnion/Experian/XDS) | With tenant consent | Duration of tenancy |
| 9 | Lease agreement | Stage 5: Lease Execution | Landlord/agent/attorney | RHA s5(2) | Duration of tenancy + 3 years (prescription) |
| 10 | House rules annexure | Stage 5: Lease Execution | Landlord/body corporate | RHA s5(5) — mandatory | With lease |
| 11 | Billing schedule / debit order mandate | Stage 6: Recurring Invoice Setup | Agent/landlord | Lease terms | Duration of tenancy + 3 years |
| 12 | Deposit receipt | Stage 7: Deposit Payment | Landlord/agent | RHA s5(3)(f) | Duration of tenancy + 3 years |
| 13 | Outgoing inspection report | Stage 8: Move-Out Inspection | Joint — landlord + outgoing tenant | RHA deposit provisions | 3 years after termination |
| 14 | Snag list / contractor invoices | Stage 9: Repairs & Cleaning | Landlord/agent | Best practice | 3 years after termination |
| 15 | Ingoing inspection report | Stage 10: Move-In Inspection | Joint — landlord + new tenant | RHA s5(3) | Duration of tenancy + 3 years |
| 16 | Inventory list (furnished) | Stage 10: Move-In Inspection | Joint — landlord + new tenant | Best practice | Duration of tenancy + 3 years |
| 17 | Key register / welcome pack | Stage 11: Onboarding | Agent/landlord | Best practice | Duration of tenancy |
| 18 | Utilities transfer forms | Stage 11: Onboarding | Agent/landlord + tenant | Municipal requirements | Duration of tenancy |
| 19 | Rent receipts | Stage 12: Rent Collection | Landlord/agent | RHA s5A | 5 years (tax records) |
| 20 | Maintenance request records | Stage 13: Maintenance | Tenant initiates; landlord/agent records | Best practice | Duration of tenancy + 3 years |
| 21 | CPA s14 renewal notice | Stage 14: Notice (cycle) | Landlord/agent | CPA s14 | 3 years |
| 22 | Breach notice | Any stage (upon breach) | Aggrieved party | CPA / common law | 3 years after termination |
| 23 | Deposit refund statement | Stage 15: Deposit Refund | Landlord/agent | RHA s5(3)(h) | 3 years after refund |

---

## Detailed Document Descriptions

### 1. Mandate Agreement
Formal agreement between landlord and estate agent authorising the agent to market and let the property.
- **Types**: Sole mandate, open mandate, procurement-only mandate
- **Must include**: Commission rate, duration, property details, marketing scope, termination terms
- **Agent requirement**: Must hold valid Fidelity Fund Certificate (PPA 22/2019)

### 2. FICA Documents
Identity and address verification documents required by the Financial Intelligence Centre Act.

**From tenants:**
- South African ID (green barcoded or Smart ID card) OR valid passport (foreign nationals)
- Proof of residential address (less than 12 months old): utility bill, bank statement, retail account, cell phone statement
- **Not acceptable as proof of address**: Post box numbers

**From landlords:**
- Same ID and address requirements
- Company registration documents (if corporate landlord)
- Tax clearance certificate (if applicable)

**Verification**: Agent must view originals in person and retain certified copies for 5 years

### 3–5. Application and Screening Documents
- **Application form**: Personal details, employment info, current address, references, consent for checks
- **POPIA consent**: Specific consent for credit checks, employment verification, criminal record check, and data processing for lease administration
- **Credit check**: Run through registered credit bureaus with tenant's written consent

### 6. Lease Agreement
Written contract containing all terms of the rental. See `lease-rental-agreement` skill for generation.

**Mandatory contents (RHA s5(3)):**
- Names and addresses of parties
- Description of dwelling
- Term of lease and notice period (minimum 1 calendar month)
- Rental amount and escalation
- Deposit amount
- Obligation to invest deposit in interest-bearing account
- Deposit refund terms

### 7. House Rules Annexure
**Mandatory per RHA s5(5)** if house rules exist. Typically covers:
- Noise levels and quiet hours
- Pet policies
- Parking allocation
- Common area usage
- Visitor policies
- Refuse disposal
- Smoking restrictions
- Body corporate conduct rules (sectional title)

### 8. Ingoing Inspection Report
**Mandatory joint inspection** — both landlord and tenant must attend.

**Must include:**
- Date and time of inspection
- Room-by-room condition assessment (walls, floors, ceilings, fixtures, fittings)
- Pre-existing defects noted in detail
- Date/time-stamped photographs or video
- Signatures of both parties
- 3 copies: tenant, landlord, agent (if applicable)

**Critical**: Without this report, landlord loses the right to claim damages from the deposit.

### 9. Inventory List (Furnished Properties)
Detailed list of all furnishings, appliances, and contents provided with the property.
- Item description, condition, quantity
- Photographs of each item
- Signed by both parties
- Used for damage comparison at move-out

### 10. Deposit Receipt
Proof that deposit was received and placed in an interest-bearing account.
- Amount received
- Date received
- Bank name and account details
- Interest rate applicable
- Tenant entitled to request proof of accrued interest at any time

### 11–12. Ongoing Records
- **Rent receipts**: Must be issued on tenant's request (RHA s5A)
- **Maintenance records**: Written requests, responses, completion records — critical for dispute resolution

### 13. CPA Section 14 Renewal Notice
Landlord must notify tenant **40–80 business days before lease expiry** about:
- That the lease is expiring
- Renewal options and proposed new terms
- Any rental escalation
- Failure to notify → lease automatically continues month-to-month on same terms

### 14–15. Termination and Breach Notices
- **Termination notice**: Written, delivered with proof (email, registered post, hand delivery)
- **Breach notice**: Must specify the breach, give 20 business days to remedy, and warn of cancellation if not remedied

### 16. Outgoing Inspection Report
Same format as ingoing inspection — compared side by side to determine:
- Fair wear and tear (landlord's cost)
- Tenant damage (deductible from deposit)
- Both parties should attend and sign
- Date/time-stamped comparison photos

### 17. Deposit Refund Statement
Itemised breakdown provided to tenant:
- Original deposit amount
- Interest accrued
- Each deduction with description and supporting invoice/quotation
- Net refund amount
- Payment method and date

### 18. Compliance Certificates

| Certificate | Required for | Validity | Issued by |
|---|---|---|---|
| Electrical Certificate of Compliance (CoC) | All properties at change of occupancy | 2 years | Registered electrician |
| Gas Certificate of Compliance | Properties with gas installations | 2 years | Registered gas installer |
| Electric Fence Compliance Certificate | Properties with electric fencing | 2 years | Registered installer |
| Beetle/Entomology Certificate | Some areas (coastal) / buyer requirement | As issued | Pest control company |
| Plumbing Certificate of Compliance | New installations | As issued | Registered plumber |

**Note**: Electrical CoC is the most commonly required at change of tenancy. Check municipal and provincial requirements.

# Roles, Responsibilities, and Data Access in SA Property Rentals

How each party in the SA rental ecosystem operates, what they can do, what data they access, and the regulatory constraints — structured for security model cross-referencing.

---

## 1. Agency (Business Entity)

The registered legal entity that employs or contracts individual property practitioners.

**Legal identity:**
- Registered with PPRA (Property Practitioners Regulatory Authority)
- Must hold a valid **Fidelity Fund Certificate (FFC)** at entity level
- Every director, member, trustee, and partner must also hold individual FFCs
- Must hold valid BEE certificate and tax clearance certificate

**What the agency owns/controls:**
- Trust account(s) — holds deposits, rent, and other client money in a registered bank
- Client database — all tenants, owners, and properties under management
- Agent employment/contractor relationships
- Mandate agreements with property owners
- Compliance records (FICA, audit reports, FFC renewals)

**Data scope:**
- All properties managed by the agency (across all owners)
- All tenants across all managed properties
- All agents' transaction records and activities
- All financial records (trust account, commissions, fees)
- Audit trails of who accessed what

**Actions:**
- Appoint and oversee individual agents
- Open and manage trust accounts
- Set internal policies for data handling and compliance
- Authorise payments and disbursements from trust account
- Submit annual audit reports to PPRA (within 6 months of year-end)
- Generate financial reports for owners

**Regulatory constraints:**
- Trust account must be separate from operating account
- Monthly reconciliation of trust accounts required
- Annual audit by independent auditor
- PPRA may inspect without prior notice during business hours
- Trading without valid FFC = minimum R25,000 fine
- Cannot compel consumers to use specific service providers (PPA)

---

## 2. Estate Agent / Rental Agent (Individual Person)

A property practitioner who finds tenants and facilitates lease agreements. Transaction-focused — involvement typically ends once the tenant is placed.

**Regulatory status:**
- Must hold individual FFC (separate from agency FFC)
- Must work under a registered agency
- Accountable institution under FICA 38/2001

**Data access:**
- Tenant personal information for transactions they handle (name, ID, contact, FICA docs, credit check)
- Owner/landlord information for properties they're mandated to let
- Property details and listing information
- Financial details of the specific transaction (deposit amount, first month's rent, commission)

**Data they should NOT access:**
- Other agents' transactions or clients
- Ongoing tenant data after the transaction completes (unless also acting as managing agent)
- Owner financial summaries beyond the specific transaction
- Trust account balances or other owners' financial data

**Actions:**
- Market properties (listings, viewings, advertising)
- Screen tenants (credit checks, references, employment verification — with consent)
- Collect and verify FICA documents
- Facilitate lease agreement signing
- Collect deposit and first month's rent (must deposit into trust account immediately)
- Conduct move-in inspection
- Hand over keys

**Regulatory constraints:**
- Cannot trade without valid FFC
- Must deposit all client money into trust account "forthwith" (immediately)
- Cannot hold personal signing authority on trust accounts
- Must retain FICA records for 5 years
- Must obtain POPIA consent before collecting personal information
- Cannot discriminate when letting (RHA s4A)

---

## 3. Managing Agent (Individual Person)

A property practitioner who manages properties on an ongoing basis after the lease is signed. Relationship-focused — continuous involvement throughout the tenancy.

**Regulatory status:**
- Must hold Managing Agent FFC category (distinct from sales FFC)
- Must be registered with PPRA
- Can be an employee of the agency or independent contractor

**Data access:**
- Full operational access to all properties assigned to them
- Tenant personal information for assigned properties (name, contact, ID, lease terms, payment history)
- Owner information for assigned properties (contact, financials, payment preferences)
- Maintenance records, inspection reports, and communications
- Financial records: rent collected, expenses, arrears, statements
- Supplier/contractor details for assigned properties

**Data they should NOT access:**
- Properties not assigned to them (even within the same agency)
- Agency-level financial data (unless also an agency principal)
- Other managing agents' property portfolios
- Commission structures of other agents

**Actions:**
- Collect rent and manage arrears
- Manage deposits (invest, track interest, process refunds)
- Screen and onboard tenants
- Coordinate maintenance (receive requests, appoint contractors, approve quotes)
- Conduct periodic, move-in, and move-out inspections
- Process lease renewals and serve notices on behalf of owner
- Communicate with tenants on operational matters
- Generate financial reports and statements for owners
- Pay suppliers from trust account (with authorisation)

**Key difference from estate agent:**
- **Estate agent**: Transaction-based, limited duration, procurement focus
- **Managing agent**: Ongoing relationship, continuous data access, operational management
- Managing agent has broader and deeper data access because their role is continuous

---

## 4. Property Owner / Landlord

The registered owner of the property who lets it to tenants — either self-managing or via an agency.

**Data access (own properties only):**
- Full details of their own property/properties and units
- Tenant information for their properties: name, contact, lease terms, payment history
- Financial summaries: rent collected, expenses, net income, statements
- Inspection reports and maintenance records for their properties
- Deposit status and interest accrued for their tenants
- Municipal account information for their properties

**Data they should NOT access:**
- Other owners' properties, tenants, or financials (even if managed by the same agency)
- Agent commission structures or agency internal data
- Other tenants in a complex who are not their tenants
- Agency trust account balances beyond their own property transactions

**Actions (self-managing):**
- Everything a managing agent does, but for their own properties
- Full autonomy over tenant selection, rent setting, maintenance decisions
- Must still comply with RHA, CPA, POPIA, PIE Act

**Actions (using an agency):**
- Approve/reject prospective tenants (final say)
- Set rental amounts and escalation rates
- Approve or reject maintenance quotes above agreed thresholds
- Review financial statements and reports
- Request inspections
- Instruct agent to serve notices
- Does NOT directly interact with tenants in most cases (goes through managing agent)

**Regulatory constraints:**
- Ultimately liable for municipal rates and services on the property
- Liable for body corporate levies (sectional title)
- Must declare rental income to SARS
- Cannot cut utilities or change locks (RHA s4A, PIE s8)
- Must comply with POPIA when handling tenant data (even if self-managing)
- Deposit must be in interest-bearing account (RHA s5(3)(f))

---

## 5. Tenant

The person occupying the property under a lease agreement.

**Data access (own tenancy only):**
- Their own lease agreement and any addendums
- Their own payment history and rent receipts
- Their own deposit amount and accrued interest
- Their own maintenance requests and status updates
- Their own inspection reports (ingoing and outgoing)
- Their own communications with landlord/agent
- House rules / conduct rules applicable to them

**Data they should NOT access:**
- Other tenants' personal information, leases, or payment history
- Owner/landlord financial details (profit, expenses, bond information)
- Agent commission rates or agency internal data
- Other units' maintenance requests or tenant details
- Building-level financial data (unless they are a body corporate member, which tenants are not)

**Actions:**
- Pay rent on agreed date
- Submit maintenance requests
- Request rent receipts (RHA s5A)
- Request proof of deposit interest
- View their lease and payment history
- Communicate with landlord/managing agent
- Attend inspections

**POPIA rights (data subject):**
- Request access to all personal information held about them (s23)
- Request correction of inaccurate information (s24)
- Request deletion of personal information — subject to legal retention requirements (s24)
- Object to processing of personal information (s11(3)(b))
- Be informed of data breaches affecting them (s22)
- Lodge complaint with Information Regulator

**Regulatory protections:**
- Right to written lease (RHA s5(2))
- Right to habitable premises (RHA s5A)
- Protection from illegal eviction (PIE Act)
- Cannot be discriminated against (RHA s4A)
- Utilities cannot be cut for rent non-payment (RHA s4A)
- Deposit must be refunded within prescribed timelines (RHA s5(3)(h))

---

## 6. Supplier / Contractor

Service provider who performs maintenance, repairs, or other services on rental properties.

**Data access (assigned jobs only):**
- Property address and access instructions for the specific job
- Tenant contact details — **minimum necessary** (name, phone number for access coordination)
- Description of the maintenance issue / scope of work
- Agreed quote amount and payment terms

**Data they should NOT access:**
- Tenant's full personal profile (ID number, lease terms, payment history, other requests)
- Owner financial details
- Other properties' maintenance requests
- Other tenants' information
- Building-level data or agency internal data

**Actions:**
- Complete assigned maintenance/repair work
- Communicate with managing agent about job status and completion
- Submit invoices for completed work
- Access the property at scheduled times (with tenant notification)

**Regulatory constraints:**
- POPIA data minimisation — can only receive information necessary for the job
- Purpose limitation — data received can only be used for completing the work
- Cannot share tenant information with other parties
- Must protect any personal information received

---

## Role Hierarchy and Data Isolation

```
Agency (top-level entity)
 ├── Agent A (sees only own transactions)
 ├── Agent B (sees only own transactions)
 ├── Managing Agent X (sees assigned properties)
 │    ├── Owner 1 (sees own properties only)
 │    │    ├── Property A
 │    │    │    ├── Tenant 1 (sees own data only)
 │    │    │    └── Tenant 2 (sees own data only)
 │    │    └── Property B
 │    │         └── Tenant 3 (sees own data only)
 │    └── Owner 2 (sees own properties only)
 │         └── Property C
 │              └── Tenant 4 (sees own data only)
 └── Managing Agent Y (sees assigned properties)
      └── Owner 3 (sees own properties only)
           └── Property D
                └── Tenant 5 (sees own data only)

Supplier/Contractor → sees ONLY assigned job details (crosses into any property temporarily)
```

**Critical isolation rules:**
- Owner 1 cannot see Owner 2's data (even if managed by the same agent)
- Tenant 1 cannot see Tenant 2's data (even in the same property)
- Agent A cannot see Agent B's transactions
- Managing Agent X cannot see Managing Agent Y's properties
- Agency sees everything across all agents, owners, and properties
- Suppliers see only the specific job they're assigned to

---

## Action Permission Matrix

| Action | Agency | Agent | Managing Agent | Owner | Tenant | Supplier |
|---|---|---|---|---|---|---|
| List/market property | Y | Y (mandated) | Y | Y (self-manage) | N | N |
| Screen tenants | Y | Y | Y | Y (self-manage) | N | N |
| Sign lease | Y | Y | Y | Y | Y (own lease) | N |
| Collect deposit/rent | Y | Y (initial) | Y | Y (self-manage) | N | N |
| Manage trust account | Y | N | N | N | N | N |
| Conduct inspections | Y | Y | Y | Y | Attend only | N |
| Approve maintenance | Y | N | Y (within threshold) | Y (above threshold) | N | N |
| Submit maintenance request | N | N | Y (on behalf) | Y | Y | N |
| Complete maintenance work | N | N | N | N | N | Y |
| Serve notices | Y | Y | Y | Y (self-manage) | N | N |
| View financial reports | Y (all) | Own transactions | Assigned properties | Own properties | Own payments | Own invoices |
| Process deposit refund | Y | N | Y | Y (self-manage) | N | N |
| Access tenant PII | Y | Own transactions | Assigned properties | Own tenants | Own data | Minimum for job |
| Lodge Tribunal complaint | N | N | N | Y | Y | N |
| Approve tenant application | Y | N | Y (recommend) | Y (final say) | N | N |

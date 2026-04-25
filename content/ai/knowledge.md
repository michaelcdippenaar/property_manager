# Klikk Domain Rules

This file is the authoritative source of domain knowledge injected into the AI Guide
system prompt. Edit it via the Admin portal (Settings → AI Knowledge) or directly in
this file. Changes take effect within 5 minutes (cache TTL) or immediately after saving
via the admin UI.

---

## Tenant Management

- **Tenants are created via lease creation — there is no standalone "Add Tenant" flow.**
  When an agent asks to "add a tenant", the correct response is to navigate to lease
  creation, where the tenant record is created as part of the lease.
- A tenant's account is linked to one active lease at a time. Multiple leases in
  `draft` or `expired` state may exist for auditing purposes.

## Roles and Terminology

- **Owner and Landlord are the same entity.** The data model uses the term "landlord"
  (e.g. `Landlord` model, `landlord_id` foreign keys). In the UI and communications,
  the term "owner" is used for readability. Do not confuse these — they refer to
  the same person.
- **Agent roles:** There are three agent variants — `estate_agent`, `managing_agent`,
  and `agency_admin`. All three have access to the agent portal. `agency_admin` also
  has access to agency-level settings.
- **Supplier** refers to a contractor or service provider who handles maintenance work.
  Suppliers see only the jobs assigned to them — they do not have property or lease access.

## Properties and Vacancy

- **A property without an active lease is "vacant".** A lease must be in `active` status
  to count as occupying a unit. Leases in `pending`, `draft`, or `expired` state do not
  occupy a unit — the property remains vacant.
- Properties can have multiple units (e.g. a block of flats). Each unit tracks its own
  vacancy status independently.

## Maintenance Workflow

- **Maintenance requests originate from tenants and route to suppliers via the agent.**
  The flow is: Tenant submits request → Agent reviews and assigns → Supplier receives job.
- Agents can also create maintenance requests on behalf of tenants (e.g. after a phone
  call). Suppliers cannot create or modify requests — they can only update job status
  (accept, complete).
- Maintenance categories: Plumbing, Electrical, General, Structural, Pest Control,
  Security, HVAC, Garden.

## Lease Lifecycle

- Lease statuses in order: `draft` → `pending` (sent for signing) → `active` (signed
  and commenced) → `expired` (end date passed) or `terminated` (early exit).
- Only `active` leases occupy a unit and grant tenant portal access.
- Rent is collected against an `active` lease. Payments cannot be recorded against a
  `draft` or `expired` lease.

## Payments and Financials

- Rent payments are recorded in ZAR (South African Rand). All financial figures are in
  ZAR unless explicitly stated otherwise.
- Payment statuses: `pending`, `paid`, `overdue`, `partial`, `reversed`.
- A deposit is held separately from monthly rent. It is returned (or deducted from) at
  lease termination, governed by the Rental Housing Act (RHA).

## South African Context

- This platform operates under South African law: Rental Housing Act (RHA), Protection
  of Personal Information Act (POPIA), and the Prevention of Illegal Eviction Act (PIE).
- Evictions must follow the PIE Act process — the platform does not automate eviction
  but can track notice-to-vacate events.
- POPIA s72 requires that personal information shared with third-party services (such as
  AI providers) is scrubbed of identifiers before transmission.

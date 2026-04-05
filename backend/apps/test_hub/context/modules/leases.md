# Module: leases

**App path:** `apps/leases/`
**Domain:** Rental lease agreements, lease templates (TipTap HTML), AI-assisted builder, reusable clauses, RHA compliance.

---

## Models

| Model | Key Fields |
|-------|-----------|
| `Lease` | `unit` (FK→Unit), `primary_tenant` (FK→Person), `start_date`, `end_date`, `monthly_rent`, `deposit`, `status` (active/pending/expired/terminated), `lease_number` (auto: `L-YYYYMM-NNNN`), `payment_reference`, `water_terms`, `electricity_terms`, `notice_period`, `ai_parse_result` (JSON) |
| `LeaseTemplate` | `name`, `content` (TipTap HTML with `{{merge_fields}}`), `description`, `is_default` |
| `LeaseBuilderSession` | AI-assisted session that builds a Lease. Fields: `agent` (FK→User), `unit` (FK→Unit), `template` (FK→LeaseTemplate), `session_data` (JSON), `status` (draft/complete) |
| `LeaseTenant` | Co-tenant on a lease. Fields: `lease` (FK→Lease), `person` (FK→Person), `is_primary` |
| `LeaseOccupant` | Additional occupant (not on the lease contract). Fields: `lease` (FK→Lease), `full_name`, `id_number`, `relationship` |
| `LeaseGuarantor` | Guarantor / co-debtor. Fields: `lease` (FK→Lease), `person` (FK→Person), `relationship` |
| `ReusableClause` | Reusable text block. Fields: `title`, `content` (HTML), `tags` (M2M or JSON), `is_active` |
| `LeaseEvent` | Calendar event tied to a lease. Fields: `lease` (FK→Lease), `event_type` (inspection/renewal/notice/etc.), `date`, `title`, `notes` |
| `OnboardingStep` | Tracks tenant onboarding checklist items per lease. Fields: `lease` (FK→Lease), `step_key`, `completed_at` |
| `LeaseDocument` | File attached to a lease. Fields: `lease` (FK→Lease), `document_type`, `file`, `uploaded_by` |

---

## Template System

Templates use TipTap HTML stored in `LeaseTemplate.content`. Merge fields are wrapped
in double curly braces: `{{tenant_name}}`, `{{unit_address}}`, `{{monthly_rent}}`, etc.

Key merge field categories:
- Tenant fields: `{{tenant_name}}`, `{{tenant_id_number}}`, `{{tenant_phone}}`
- Property fields: `{{property_name}}`, `{{unit_number}}`, `{{unit_address}}`
- Lease fields: `{{start_date}}`, `{{end_date}}`, `{{monthly_rent}}`, `{{deposit}}`, `{{notice_period}}`
- Landlord fields: `{{landlord_name}}`, `{{landlord_reg_number}}`

Before generating a PDF, all merge fields must be resolved. An unresolved merge field
(`{{...}}` still present) is a test failure condition.

---

## Lease Builder

`LeaseBuilderSession` is an AI-assisted multi-step process:

1. Agent selects a unit and template → session created
2. AI asks clarifying questions (via chat in builder UI)
3. Agent answers; session_data accumulates facts
4. AI generates populated lease HTML
5. Agent reviews, edits in TipTap
6. Session finalized → Lease record created

Builder sessions are associated with a single agent user. Only the creating agent (or admin)
can access a session.

---

## Reusable Clauses

`ReusableClause` records are searchable text blocks that can be inserted into templates.
They are tagged (e.g. `"pet_policy"`, `"parking"`, `"early_termination"`) and can be
searched by tag or full-text. The TipTap editor has a clause picker UI.

---

## Lease Events

`LeaseEvent` ties calendar events to a lease:
- `inspection` — scheduled property inspection
- `renewal` — lease renewal negotiation window
- `notice` — formal notice served
- `payment` — rent payment reminder

Events drive the calendar view in the admin portal.

---

## RHA Compliance

The South African Rental Housing Act requires:
- Notice period of at least 1 calendar month (20 business days)
- Deposit must be held in interest-bearing account
- Landlord must provide written lease within 7 days
- Water and electricity terms must be specified

Tests should verify that lease creation rejects RHA-invalid configurations
(e.g. `notice_period < 20`).

---

## API Endpoints

```
GET/POST      /api/v1/leases/                    — list / create leases
GET/PATCH/DELETE /api/v1/leases/{id}/            — retrieve / update / delete
GET/POST      /api/v1/leases/{id}/documents/     — upload / list lease documents
POST          /api/v1/leases/parse-document/     — AI lease parsing (Claude)
POST          /api/v1/leases/import/             — Import from parsed PDF result
GET/POST      /api/v1/leases/templates/          — list / create templates
GET/POST      /api/v1/leases/builder/sessions/   — list / create builder sessions
POST          /api/v1/leases/builder/sessions/{id}/message/ — AI chat turn
POST          /api/v1/leases/builder/sessions/{id}/finalize/ — produce Lease
GET/POST      /api/v1/leases/clauses/            — reusable clause CRUD
GET/POST      /api/v1/leases/{id}/events/        — lease event CRUD
```

---

## Key Invariants

- `start_date` must be before `end_date`
- `monthly_rent` must be positive (> 0)
- `deposit` must be >= 0
- `primary_tenant` must reference a valid `Person`
- A lease's `unit` cannot be reassigned after creation
- `lease_number` is auto-generated and unique; never supplied by the client
- `OnboardingStep.step_key` must be unique per lease (no duplicate steps)
- `LeaseGuarantor` person must be different from the primary tenant

---

## Integration Dependencies

- **DocuSeal** (`apps/esigning`) — e-signing submissions are created from a Lease
- **Gotenberg** (`apps/esigning`) — PDF generated from template HTML + merge fields
- **Anthropic Claude** — `POST /leases/parse-document/` and builder AI chat

---

## Known Test Areas

- Lease CRUD: create with valid data → 201; invalid dates → 400
- Permission: only agent/admin can create leases; tenant gets 403
- Template: create template with merge fields; retrieve; update content
- Builder session: create → message exchange → finalize → lease created
- Clause: create, tag, search by tag, insert into template
- Template merge field audit: all `{{fields}}` in content are resolvable
- AI parse: mock Claude response → import endpoint creates correct Lease
- Lease document upload: PDF accepted; unsupported type rejected
- Lease events: create, list, filter by event_type

---

## Coverage Gaps

- `OnboardingStep` tests (step creation, completion tracking)
- `LeaseGuarantor` edge cases (same person as tenant, missing person)
- RHA compliance enforcement in serializer validation
- Lease number uniqueness under concurrent creation
- Builder session access control (other agent cannot access)

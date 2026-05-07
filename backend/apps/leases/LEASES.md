# Leases App

Lease lifecycle management with AI-powered document parsing, conversational lease builder, template editing, and reusable clause library.

## Overview

The leases app is the most feature-rich module. It manages the full lease lifecycle: creating leases (manually or via AI), managing tenants/occupants/guarantors, calendar events, onboarding steps, document uploads, PDF parsing, template management with AI-assisted editing, a conversational lease builder, and a reusable clause library with AI generation/extraction.

---

## Models

### Lease

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `unit` | ForeignKey → Unit | Rental unit |
| `primary_tenant` | ForeignKey → Person | Primary lessee (nullable) |
| `start_date` | DateField | Lease start |
| `end_date` | DateField | Lease end |
| `monthly_rent` | DecimalField(10,2) | Monthly rental |
| `deposit` | DecimalField(10,2) | Security deposit |
| `status` | CharField | `active`, `expired`, `terminated`, `pending`. Auto-flipped active → expired by the daily `expire_leases` cron when `end_date < today` (see [Lease expiry job](#lease-expiry-job)). |
| `max_occupants` | PositiveSmallIntegerField | Default: 1 |
| `water_included` | BooleanField | Default: true |
| `water_limit_litres` | PositiveIntegerField | Default: 4000 |
| `electricity_prepaid` | BooleanField | Default: true |
| `notice_period_days` | PositiveSmallIntegerField | Default: 20 |
| `early_termination_penalty_months` | PositiveSmallIntegerField | Default: 3 |
| `lease_number` | CharField(50) | Auto-generated: `L-YYYYMM-XXXX` |
| `payment_reference` | CharField(100) | Payment reference |
| `ai_parse_result` | JSONField | Audit trail from document parsing (nullable) |
| `created_at` | DateTimeField | Auto-set |

### LeaseTemplate

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(200) | Template name |
| `version` | CharField(20) | Version (default: "1.0") |
| `province` | CharField(100) | Province scope (blank = national) |
| `docx_file` | FileField | Uploaded DOCX/PDF |
| `fields_schema` | JSONField | Auto-discovered merge field names |
| `content_html` | TextField | Editable HTML content |
| `header_html` | TextField | Page header HTML |
| `footer_html` | TextField | Page footer HTML |
| `is_active` | BooleanField | Default: true |

### LeaseBuilderSession

| Field | Type | Description |
|-------|------|-------------|
| `created_by` | ForeignKey → User | Agent who started the session |
| `template` | ForeignKey → LeaseTemplate | Template used (nullable) |
| `lease` | OneToOneField → Lease | Created lease (set on finalize) |
| `messages` | JSONField | Chat history `[{role, content}]` |
| `current_state` | JSONField | Extracted lease field values |
| `rha_flags` | JSONField | RHA compliance warnings `[{field, severity, message}]` |
| `status` | CharField | `drafting`, `review`, `finalized` |

### LeaseTenant (Co-tenants)

| Field | Type | Unique |
|-------|------|--------|
| `lease` | ForeignKey → Lease | (lease, person) |
| `person` | ForeignKey → Person | |

### LeaseOccupant

| Field | Type | Description |
|-------|------|-------------|
| `lease` | ForeignKey → Lease | |
| `person` | ForeignKey → Person | |
| `relationship_to_tenant` | CharField(50) | e.g. "spouse", "child" |

### LeaseGuarantor

| Field | Type | Description |
|-------|------|-------------|
| `lease` | ForeignKey → Lease | |
| `person` | ForeignKey → Person | |
| `covers_tenant` | ForeignKey → Person | Which tenant's obligations (nullable) |

### ReusableClause

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField(200) | Clause title |
| `category` | CharField | `parties`, `premises`, `financial`, `utilities`, `legal`, `signatures`, `general` |
| `html` | TextField | HTML content |
| `tags` | JSONField | Tag list |
| `source_templates` | M2M → LeaseTemplate | Origin templates |
| `use_count` | PositiveIntegerField | Times used |
| `created_by` | ForeignKey → User | |

### LeaseEvent

| Field | Type | Description |
|-------|------|-------------|
| `lease` | ForeignKey → Lease | |
| `event_type` | CharField | `contract_start`, `contract_end`, `deposit_due`, `first_rent`, `rent_due`, `inspection_in`, `inspection_out`, `inspection_routine`, `notice_deadline`, `renewal_review`, `custom` |
| `title` | CharField(200) | Event title |
| `date` | DateField | Event date |
| `status` | CharField | `upcoming`, `due`, `completed`, `overdue`, `cancelled` |
| `is_recurring` | BooleanField | |
| `recurrence_day` | PositiveSmallIntegerField | Day of month (nullable) |

### OnboardingStep

| Field | Type | Description |
|-------|------|-------------|
| `lease` | ForeignKey → Lease | |
| `step_type` | CharField | `deposit_payment`, `lease_signed`, `id_verified`, `move_in_inspection`, `key_handover`, `invoicing_setup`, `tenant_app_setup`, `welcome_sent` |
| `title` | CharField(200) | Step title |
| `is_completed` | BooleanField | |
| `order` | PositiveSmallIntegerField | Display order |

### LeaseDocument

| Field | Type | Description |
|-------|------|-------------|
| `lease` | ForeignKey → Lease | |
| `document_type` | CharField | `signed_lease`, `id_copy`, `other` |
| `file` | FileField | Upload to `lease_documents/` |
| `description` | CharField(200) | |

---

## API Endpoints

All endpoints prefixed with `/api/v1/leases/`.

---

### Lease CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | List leases (role-filtered) |
| `POST` | `/` | Create lease |
| `GET` | `/{id}/` | Retrieve (with documents, tenants, occupants, guarantors) |
| `PATCH` | `/{id}/` | Update |
| `DELETE` | `/{id}/` | Delete |

**Auth:** Required. **Filters:** `status`, `unit`.

**Role filtering:** Tenants see their own leases. Agents see leases for their properties. Admins see all.

---

### Lease Documents

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{id}/documents/` | List documents |
| `POST` | `/{id}/documents/` | Upload document (multipart) |
| `DELETE` | `/{id}/documents/{doc_id}/` | Delete document |

---

### Lease Tenants

```
POST   /{id}/tenants/          — Add tenant (sets as primary if none exists, otherwise co-tenant)
DELETE /{id}/tenants/{person_id}/ — Remove tenant (promotes co-tenant to primary if needed)
```

**Request:** `{"person_id": 123}` or `{"person": {"full_name": "...", ...}}`

---

### Lease Occupants

```
POST   /{id}/occupants/              — Add occupant
DELETE /{id}/occupants/{occupant_id}/ — Remove occupant
```

**Request:** `{"person_id": 123, "relationship_to_tenant": "spouse"}`

---

### Lease Guarantors

```
POST   /{id}/guarantors/                — Add guarantor
DELETE /{id}/guarantors/{guarantor_id}/ — Remove guarantor
```

**Request:** `{"person_id": 123, "covers_tenant_id": 456}`

---

### Lease Events & Calendar

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{id}/events/` | List events for a lease |
| `POST` | `/{id}/events/` | Create custom event |
| `PATCH` | `/{id}/events/{event_id}/` | Update event (auto-sets completed_at) |
| `POST` | `/{id}/generate-events` | Auto-generate all standard events + onboarding steps |
| `GET` | `/calendar/` | Cross-lease calendar (`?from=YYYY-MM-DD&to=YYYY-MM-DD`) |

---

### Onboarding Steps

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{id}/onboarding/` | List onboarding steps |
| `PATCH` | `/{id}/onboarding/{step_id}/` | Mark step complete/incomplete |

---

### Document Parsing (AI)

```
POST /api/v1/leases/parse-document/
```

Upload a lease PDF. Claude extracts structured data (tenants, rent, dates, property details).

**Request:** `multipart/form-data` with `file` (PDF, max 32 MB)

**Response:** `200 OK` — Extracted lease data as JSON (tenants, amounts, dates, property info).

---

### Lease Import

```
POST /api/v1/leases/import/
```

Atomic import from parsed data. Creates Property, Unit, Persons, and Lease in a single transaction.

**Response:** `201 Created` — `{"id": 789, "status": "pending", "lease_number": "L-202603-0001"}`

---

### Template Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/templates/` | List active templates |
| `POST` | `/templates/` | Upload DOCX/PDF template |
| `GET` | `/templates/{id}/` | Detail (includes detected_variables) |
| `PATCH` | `/templates/{id}/` | Update metadata |
| `DELETE` | `/templates/{id}/` | Delete |
| `GET` | `/templates/{id}/preview/` | Get template structure for editor |
| `GET` | `/templates/{id}/export.pdf/` | Download as PDF with visible merge field blanks |

---

### Template AI Chat

```
POST /templates/{id}/ai-chat/
```

Interactive AI-powered document editing with Claude. Supports tools: `edit_lines`, `update_all`, `apply_formatting`, `insert_toc`, `renumber_sections`, `add_comment`, `highlight_fields`.

**Request:**

```json
{
  "message": "Make the deposit clause more tenant-friendly",
  "api_history": [...]
}
```

**Response:**

```json
{
  "reply": "I've updated the deposit terms...",
  "document_update": {
    "html": "...",
    "summary": "Deposit clause updated."
  }
}
```

---

### Document Generation

```
POST /api/v1/leases/generate/
```

Fill template with context and return rendered DOCX.

---

### Reusable Clause Library

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/clauses/` | List clauses (`?category=...&q=...`) |
| `POST` | `/clauses/` | Save clause |
| `DELETE` | `/clauses/{id}/` | Delete |
| `POST` | `/clauses/{id}/use/` | Increment use_count |
| `POST` | `/clauses/generate/` | AI-generate clause options for a topic |
| `POST` | `/clauses/extract/` | AI-extract clauses from a template |

**Generate Request:** `{"topic": "pet policy", "category": "general", "count": 3}`

**Generate Response:**

```json
{
  "options": [
    {"title": "Strict Pet Policy", "category": "general", "html": "..."},
    {"title": "Tenant-Friendly Pet Policy", "category": "general", "html": "..."}
  ]
}
```

---

### Lease Builder (Conversational AI)

#### Create Session

```
POST /api/v1/leases/builder/sessions/
```

**Request:** `{"template_id": 1, "existing_lease_id": 123}` (both optional)

**Response:** `201 Created`

```json
{
  "session_id": 42,
  "message": "Welcome! Let's build your lease...",
  "current_state": {},
  "rha_flags": [],
  "ready_to_finalize": false,
  "required_fields": ["landlord_name", "property_address", "tenant_name", ...],
  "missing_fields": ["landlord_name", "property_address", ...],
  "template": {"id": 1, "name": "Standard Lease"}
}
```

#### Chat

```
POST /api/v1/leases/builder/sessions/{id}/message/
```

**Request:** `{"message": "The property is 123 Main Street, tenant is John Smith"}`

**Response:**

```json
{
  "reply": "Great! I've recorded the property address and tenant name...",
  "current_state": {"property_address": "123 Main Street", "tenant_name": "John Smith"},
  "rha_flags": [],
  "ready_to_finalize": false,
  "missing_fields": ["lease_start", "lease_end", "monthly_rent", ...]
}
```

Validates against South African Rental Housing Act (deposit limits, notice periods, etc.).

#### Finalize

```
POST /api/v1/leases/builder/sessions/{id}/finalize/
```

Converts session to a Lease record (atomic transaction). Returns `{"lease_id": 789, "lease_number": "L-202603-0001"}`.

---

## Security Notes

| ID | Severity | Issue |
|----|----------|-------|
| VULN-4 | Critical | **IDOR** — Lease ViewSet has no ownership filtering for agents/admins. |
| VULN-8 | Critical | **IDOR** — Any user can pass any `existing_lease_id` to pre-populate a builder session. |
| VULN-23 | Medium | **No date validation** — `end_date` before `start_date` is accepted. |

## Known Bugs

- `builder_views.py:152` — Uses `prefetch_related("tenants__person")` but the correct related name is `"co_tenants"`. Causes `AttributeError` when creating a session with `existing_lease_id`.

## Lease expiry job

A daily cron job flips active leases whose `end_date` has passed to `expired`,
which in turn re-syncs the linked Unit from `occupied` back to `available`
via the `post_save` signal on Lease.

**Module:** `apps/leases/expiry.py::expire_overdue_leases(today=None) -> int`
**Command:** `python manage.py expire_leases [--dry-run]`

**Cron** (run daily, just after midnight SAST):

```
5 0 * * * /path/to/venv/bin/python /path/to/manage.py expire_leases >> /var/log/klikk/lease_expiry.log 2>&1
```

The signal handler `_resync_unit_status` also defends against the cron being
down — it filters by `end_date >= today`, so even a stale active row never
falsely marks a unit as occupied on subsequent saves.

## Deploy notes — orphan-user check (`accounts.E003`)

The `check_no_orphan_users` system check enforces the Phase 3.1 invariant
that every staff/owner user must have an `agency_id`. It is registered with
the `security` tag, which means:

- `python manage.py migrate` does **not** run it (migrate runs `tags=["models"]` only).
- `python manage.py check` and `python manage.py check --deploy` run it.

If a fresh deploy hits orphans (legacy data), run the Phase 4 backfill
migration first (`leases`/`accounts` apps), then re-run `check --deploy`.
The check intentionally fails CI/deploy gates until orphans are repaired —
this is the security floor for multi-tenant scoping.

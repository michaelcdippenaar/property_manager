# Tenant App (`apps/tenant`)

Canonical tenant entity and property-occupancy history for the Klikk platform.

---

## Overview

The existing system tracks tenants informally across several models:
- `Person` (in `apps/accounts`) — the legal identity; also used for owners, guarantors, co-tenants
- `User` with `role=TENANT` — a portal login account; not all tenants have one
- `Lease.primary_tenant` — a FK to `Person`; contractual link to a unit
- `TenantIntelligence.unit_ref` (in `apps/ai`) — informal denorm with no date range, no history

**The gap:** there was no first-class, queryable, historically-tracked record that says
_"Person X occupied Unit Y from Date A to Date B"_ — especially for tenants who exist
outside of a formal lease (e.g. maintenance-only clients).

This app fills that gap.

---

## Identity Layers

```
Person  ─── OneToOne ───►  Tenant  ◄─── FK (optional) ───  User
(legal identity)          (this app)                      (portal login)
       │
       └── via assign_from_lease() or assign_unit()
                  │
                  ▼
       TenantUnitAssignment
       (who, which unit, when)
```

A `Person` becomes a `Tenant` when a property owner or agent registers them — either:
1. **Manually**: Owner selects a Person, picks a unit and date range → `assign_unit()`
2. **From a lease**: Derived from an existing `Lease` → `assign_from_lease()`

---

## Models

### `Tenant`

The canonical tenant record. One per Person.

| Field | Type | Description |
|-------|------|-------------|
| `person` | `OneToOneField(Person, CASCADE)` | Legal identity. Required. `related_name="tenant_profile"` |
| `linked_user` | `FK(User, SET_NULL, null=True)` | Optional portal login account. `related_name="tenant_records"` |
| `is_active` | `BooleanField(default=True)` | Is this tenant currently active in the system? |
| `notes` | `TextField(blank=True)` | Free-text agent notes |
| `created_at` | `DateTimeField(auto_now_add)` | Created timestamp |
| `updated_at` | `DateTimeField(auto_now)` | Last modified timestamp |

**`Meta`:** `ordering = ["person__full_name"]`

#### `current_assignment` property

Returns the active `TenantUnitAssignment` for today, or `None`.

Active = `start_date <= today` AND (`end_date is null` OR `end_date >= today`).

---

### `TenantUnitAssignment`

Temporal record of a tenant occupying a unit for a date range.

| Field | Type | Description |
|-------|------|-------------|
| `tenant` | `FK(Tenant, CASCADE)` | The tenant. `related_name="assignments"` |
| `unit` | `FK(Unit, PROTECT)` | Unit occupied. PROTECT prevents unit deletion while assignments exist. |
| `property` | `FK(Property, PROTECT)` | Denormalized from `unit.property` at creation time (see note below). |
| `lease` | `FK(Lease, SET_NULL, null=True)` | Linked lease, if source=LEASE. Null for manual assignments. |
| `start_date` | `DateField()` | Inclusive start of occupancy. |
| `end_date` | `DateField(null=True)` | Inclusive end. Null = open-ended (current tenant). |
| `source` | `CharField(choices)` | `manual` or `lease` — how this was created. |
| `assigned_by` | `FK(User, SET_NULL, null=True)` | Agent/admin who created it. Null for lease-derived. |
| `notes` | `TextField(blank=True)` | Optional context. |
| `created_at` | `DateTimeField(auto_now_add)` | Created timestamp. |

**`Meta`:** `ordering = ["-start_date"]`

**Indexes:** `(tenant, start_date)` and `(unit, start_date)` for efficient history queries.

**Why denormalize `property`?**
`unit.property` is derivable at any time, but storing it directly on the assignment:
- Captures historical accuracy (the property relationship as it was at assignment time)
- Enables a single-join query for "all tenants in Property X"
- Consistent with how `MaintenanceRequest` and `TenantIntelligence` already denormalize unit/property refs

The `property` field is always set automatically by the methods below — never pass it manually.

---

## Auto-Linking Signal (`signals.py`)

When a new `User` is created (via registration, invite acceptance, or any other path),
a `post_save` signal fires and checks if an unlinked `Person` record exists with the
same **email** (case-insensitive) or **phone number**.

**Matching priority:**
1. Email (case-insensitive) — most reliable identifier
2. Phone number — fallback for OTP-only tenants who register with phone + SMS

If a match is found:
1. `Person.linked_user` is set to the new `User`
2. If that Person has a `Tenant` profile, `Tenant.linked_user` is also set

**Workflow (email):**
1. Admin adds a Person (e.g. "Jane Smith", `jane@example.com`) via Django admin or lease import
2. Admin creates a Tenant from that Person and assigns them to a unit
3. Later, Jane accepts an invite or registers with `jane@example.com`
4. Signal fires → Person and Tenant are automatically linked to her new User account
5. Jane can now access the tenant portal, chat, file maintenance requests, etc.

**Workflow (phone/OTP):**
1. Admin adds a Person (e.g. "Thabo Nkosi", phone `0821234567`)
2. Admin creates a Tenant from that Person
3. Later, Thabo's User account is created with phone `0821234567`
4. Signal fires → matches on phone → Person and Tenant auto-linked
5. Thabo can log in via OTP and access the tenant portal

**Edge cases:**
- If multiple unlinked Person records share the same email or phone, only the first match is linked
- If the Person already has a `linked_user`, it is not overwritten (filtered out by `linked_user__isnull=True`)
- If the User has neither email nor phone, the signal is skipped
- Only fires on `created=True` (new users), not on user updates
- Email is tried before phone — if both match different Person records, the email match wins

---

## Methods

### `Tenant.assign_unit(unit, start_date, end_date, assigned_by=None, notes="")`

Manually assign a tenant to a unit for a date range. No lease required.

**When to use:** Property owner selects a tenant and enters a unit + date range directly
(e.g. maintenance-only clients, informal arrangements, pre-lease occupancy).

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `unit` | `Unit` | Yes | The unit the tenant will occupy |
| `start_date` | `date` | Yes | Inclusive start of occupancy |
| `end_date` | `date \| None` | No | Inclusive end. Pass `None` for open-ended. |
| `assigned_by` | `User \| None` | No | The agent/admin creating this assignment |
| `notes` | `str` | No | Optional context |

**Returns:** `TenantUnitAssignment` (newly created)

**Raises:**
- `ValueError` if `end_date < start_date`
- `ValueError` if an overlapping assignment already exists for this `(tenant, unit)` range

**Example:**
```python
from apps.tenant.models import Tenant
from apps.properties.models import Unit
from datetime import date

tenant = Tenant.objects.get(person__full_name="Jane Smith")
unit = Unit.objects.get(pk=3)

assignment = tenant.assign_unit(
    unit=unit,
    start_date=date(2026, 3, 1),
    end_date=None,           # open-ended — she's currently living here
    assigned_by=request.user,
    notes="Maintenance-only client, no formal lease",
)
```

---

### `Tenant.assign_from_lease(lease)`

Derive a `TenantUnitAssignment` from an existing `Lease` record. Mirrors the lease's
`unit`, `start_date`, and `end_date`.

**When to use:** After a lease is created (or manually triggered), to sync the tenant's
occupancy record from the lease.

**Idempotent:** Calling this twice for the same lease returns the existing assignment —
no duplicate is created.

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `lease` | `Lease` | The lease to derive the assignment from |

**Returns:** `TenantUnitAssignment` (new or existing)

**Raises:**
- `ValueError` if `lease.unit` is None
- `ValueError` if `lease.primary_tenant` does not match this Tenant's Person
- `ValueError` if a conflicting assignment already exists for `(tenant, unit)` date range

**Example:**
```python
from apps.tenant.models import Tenant
from apps.leases.models import Lease

lease = Lease.objects.get(pk=42)
tenant = Tenant.get_or_create_for_lease(lease)   # step 1: ensure Tenant exists
assignment = tenant.assign_from_lease(lease)      # step 2: sync from lease
```

---

### `Tenant.get_or_create_for_lease(lease)` *(classmethod)*

Convenience: given a `Lease`, find or create the `Tenant` for its `primary_tenant` Person.
Typically called before `assign_from_lease()`.

**Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `lease` | `Lease` | The lease whose `primary_tenant` to look up |

**Returns:** `Tenant` (existing or newly created)

**Raises:**
- `ValueError` if `lease.primary_tenant` is None

---

### `Tenant.current_assignment` *(property)*

Returns the active `TenantUnitAssignment` for today, or `None`.

Queries `assignments` filtered to assignments where:
- `start_date <= today`
- `end_date IS NULL` OR `end_date >= today`

Result is `select_related("unit", "property")` — no extra queries for unit/property access.

---

## Django Admin

### Tenant list (`/admin/tenant/tenant/`)
Columns: **Tenant Name** | **Current Unit** | **Current Property** | **Active** | **Linked User** | **Created**

Searchable by: person name, person email, person ID number, linked user email.

Filter by: `is_active`.

### Tenant detail
Shows person, linked_user, is_active, notes fields, plus:
- **Unit Assignments inline** (TabularInline) — full assignment history ordered newest first.
  - `source`, `lease`, `property`, `created_at` are read-only (system-set values).
  - `unit`, `start_date`, `end_date`, `notes` are editable for manual assignments.

### Unit Assignments list (`/admin/tenant/tenantunitassignment/`)
Separate list view for querying all assignments across tenants.
Filterable by: `source`, `property`, `unit__property`.
Date hierarchy on `start_date`.

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Overlapping assignment, same unit | `ValueError` — caller must end prior assignment first |
| Two units at same time (different units) | Allowed — tenant may hold multiple units simultaneously |
| `assign_from_lease()` called twice | Idempotent — returns the existing assignment unchanged |
| Lease has no `primary_tenant` | `ValueError` raised by `get_or_create_for_lease()` |
| Wrong Tenant calls `assign_from_lease()` | `ValueError` (person mismatch check) |
| Unit deleted while assignment exists | `PROTECT` — Django refuses the deletion |
| Lease deleted while assignment exists | `SET_NULL` — assignment preserved with `lease=None` |
| Tenant created with no assignments | Valid state — `current_assignment` returns `None` |
| Open-ended assignment vs any new assignment | Open assignment always detected as overlap for same unit |

---

## Known Limitations

**N+1 in admin list view:** `current_unit_display` and `current_property_display` call
`current_assignment` per row, which issues a DB query per tenant. Acceptable at current
scale. Fix with a `get_queryset()` override using `Prefetch` when the list grows large.

---

## REST API

Base path: `/api/v1/tenant/`

All endpoints require `IsAgentOrAdmin` permission (JWT auth).

### Tenants (`/api/v1/tenant/tenants/`)

Standard ModelViewSet — `GET` (list), `POST` (create), `GET /:id/`, `PATCH /:id/`, `DELETE /:id/`.

**Query params:**
| Param | Description |
|-------|-------------|
| `?property=<id>` | Filter to tenants with assignments on this property |

**Response fields:**
`id`, `person` (nested: `id`, `full_name`, `email`, `phone`, `id_number`), `linked_user`,
`is_active`, `notes`, `current_unit` (`{id, unit_number}` or `null`),
`current_property` (`{id, name}` or `null`), `created_at`, `updated_at`.

**Create:** send `person_id` (FK to Person).

#### Custom action: `POST /api/v1/tenant/tenants/assign-unit/`

Manually assign a tenant to a unit.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tenant_id` | int | Yes | FK to Tenant |
| `unit_id` | int | Yes | FK to Unit |
| `start_date` | date | Yes | Occupancy start |
| `end_date` | date | No | Occupancy end (null = open-ended) |
| `notes` | string | No | Optional notes |

Returns the created `TenantUnitAssignment`.

---

### Assignments (`/api/v1/tenant/assignments/`)

Standard ModelViewSet for `TenantUnitAssignment`.

**Query params:**
| Param | Description |
|-------|-------------|
| `?property=<id>` | Filter by property |
| `?unit=<id>` | Filter by unit |
| `?tenant=<id>` | Filter by tenant |

**Response fields:**
`id`, `tenant`, `tenant_name`, `tenant_email`, `tenant_phone`,
`unit`, `unit_number`, `property`, `property_name`,
`lease`, `lease_number`, `start_date`, `end_date`,
`source`, `source_display`, `assigned_by`, `notes`, `created_at`.

---

## Admin Frontend (Vue)

The **Tenants tab** on the Property Detail page (`/properties/:id`) shows all tenant-unit
assignments for that property.

**Features:**
- **Table view**: tenant name, email, unit, start/end dates, source badge, notes, actions
- **Assign tenant**: modal to select a tenant, unit, date range, and notes → calls `assign-unit` action
- **Edit tenant**: modal with two sections:
  - *Tenant Details*: edits Person fields (full_name, email, phone, id_number) via `PATCH /api/v1/auth/persons/:id/`
  - *Assignment*: edits assignment fields (start_date, end_date, notes) via `PATCH /api/v1/tenant/assignments/:id/`
- **End assignment**: sets `end_date` to today via PATCH on the assignment

---

## Future Phases

### Phase 2 — Lease Signal Integration
Post-save signal on `Lease`: when status transitions to `ACTIVE`, automatically call
`Tenant.get_or_create_for_lease(lease).assign_from_lease(lease)`.

### Phase 3 — ~~REST API~~ ✓ Done
Endpoints for agent-facing tenant management: list, create, assign unit, view history.

### Phase 4 — Maintenance Integration
Add a FK from `MaintenanceRequest.tenant` (currently FK to `User`) to also reference
the `Tenant` model for richer context.

### Phase 5 — Co-tenant Assignment
Extend `assign_from_lease()` to also create assignments for `LeaseTenant` co-signatories
(currently only `primary_tenant` is assigned).

### Phase 6 — Legacy Cleanup
Deprecate `TenantIntelligence.unit_ref` / `property_ref` in favour of
`Tenant.current_assignment` as the authoritative source of truth.

### Phase 7 — ~~Frontend~~ ✓ Done
Agent-app UI: property owner selects a tenant and assigns to a unit with a date range.
Includes edit tenant modal for updating person details and assignment dates.

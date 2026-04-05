# Module: properties

**App path:** `apps/properties/`
**Domain:** Property and unit management, landlord/banking records, owner dashboard, role-based access filtering.

---

## Models

| Model | Key Fields |
|-------|-----------|
| `Property` | `owner` (FK→Person), `agent` (FK→User), `name`, `property_type` (apartment/house/townhouse/commercial), `address`, `city`, `province`, `postal_code`, `description`, `image`, `maintenance_playbook` |
| `Unit` | `property` (FK→Property), `unit_number`, `bedrooms`, `bathrooms`, `rent_amount` (Decimal), `status` (available/occupied/maintenance), `floor` |
| `UnitInfo` | Tenant-visible information block attached to a Unit (e.g. parking, access codes, bin day) |
| `PropertyAgentConfig` | Agent-specific configuration per property (e.g. playbook notes, contact preferences) |
| `Landlord` | Landlord entity record (name, company, contact details) |
| `BankAccount` | Banking details for a Landlord (bank name, account number, branch code, account type) |
| `PropertyOwnership` | Links a `Person` (owner) to a `Property` — supports fractional ownership records |
| `PropertyGroup` | Named collection of properties. Fields: `name`, `description`, `properties` (M2M→Property). Used for bulk supplier assignment. |

---

## Access Control

**Key utility:** `get_accessible_property_ids(user)` in `apps/properties/access.py`

This function returns a queryset or list of `Property` IDs the given user is allowed to see:

| Role | Access |
|------|--------|
| `admin` | All properties |
| `agent` | Properties where `property.agent == user` |
| `owner` | Properties linked via `PropertyOwnership` where `ownership.person.linked_user == user` |
| `tenant` | Properties containing units on their active lease |
| `supplier` | Properties linked via `SupplierProperty` |

Always call `get_accessible_property_ids(user)` to filter querysets in views.
Tests must verify that each role only sees their permitted properties.

---

## Unit Statuses

| Status | Meaning |
|--------|---------|
| `available` | Empty unit, available for lease |
| `occupied` | Active tenant in residence |
| `maintenance` | Temporarily unavailable due to works |

Changing a unit to `occupied` typically happens when a lease is activated.
Tests should verify that status transitions are valid.

---

## API Endpoints

```
GET/POST   /api/v1/properties/              — list / create properties (agent/admin)
GET/PATCH/DELETE /api/v1/properties/{id}/   — retrieve / update / delete
GET/POST   /api/v1/properties/{id}/units/   — list / create units for a property
GET/POST   /api/v1/properties/groups/       — PropertyGroup CRUD
GET        /api/v1/properties/owner/dashboard/   — Owner dashboard stats
GET        /api/v1/properties/owner/properties/  — Owner's properties list
```

---

## Key Invariants

- A `Unit` must belong to a `Property` (non-nullable FK)
- `rent_amount` must be positive (> 0)
- `unit_number` must be unique within a property
- A `Property` must have at least one of `agent` or `owner` set (business rule, not always DB-enforced)
- `PropertyGroup.properties` is a many-to-many; a property can belong to multiple groups
- `BankAccount` is linked to a `Landlord`, not directly to a `Property`

---

## Integration Dependencies

This app is largely self-contained. It has no direct external API calls.
It is a dependency of:
- `leases` — Lease references Unit
- `maintenance` — MaintenanceRequest references Unit, SupplierProperty references Property
- `esigning` — indirectly through leases

---

## Known Test Areas

- Agent can create a property and list only their own properties
- Admin can list all properties
- Owner can list only their own properties (via PropertyOwnership)
- Tenant cannot create or list properties
- Unit CRUD: create, update status, retrieve
- `get_accessible_property_ids` returns correct IDs per role
- `rent_amount` validation: zero or negative rejected
- PropertyGroup: create, add/remove properties, bulk-assign supplier via attach_group

---

## Coverage Gaps

- `PropertyGroup` CRUD tests (bulk supplier assignment via group)
- `BankAccount` validation (account number format, branch code length)
- `PropertyOwnership` fractional ownership edge cases
- `UnitInfo` CRUD and access control
- Owner dashboard stats accuracy

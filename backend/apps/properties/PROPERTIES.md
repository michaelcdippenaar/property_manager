# Properties App

Property, unit, and building information management with owner portal.

## Overview

The properties app manages the core real-estate data: properties, rental units, unit info/amenities, AI agent configuration per property, and property groups. It also provides an owner-facing dashboard and property list.

---

## Models

### Property

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `owner` | ForeignKey → Person | Property owner (nullable) |
| `agent` | ForeignKey → User | Managing agent (nullable) |
| `name` | CharField(200) | Property name |
| `property_type` | CharField | `apartment`, `house`, `townhouse`, `commercial` |
| `address` | TextField | Street address |
| `city` | CharField(100) | City |
| `province` | CharField(100) | Province |
| `postal_code` | CharField(10) | Postal code |
| `description` | TextField | Property description |
| `image` | ImageField | Property photo (upload to `properties/`) |
| `created_at` | DateTimeField | Auto-set on creation |

---

### Unit

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `property` | ForeignKey → Property | Parent property (CASCADE) |
| `unit_number` | CharField(20) | Unit identifier |
| `bedrooms` | PositiveSmallIntegerField | Default: 1 |
| `bathrooms` | PositiveSmallIntegerField | Default: 1 |
| `rent_amount` | DecimalField(10,2) | Monthly rent |
| `status` | CharField | `available`, `occupied`, `maintenance` |
| `floor` | PositiveSmallIntegerField | Floor number (nullable) |

---

### UnitInfo

Additional property/unit information items (amenities, utilities, etc.).

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `property` | ForeignKey → Property | Associated property (CASCADE) |
| `unit` | ForeignKey → Unit | Specific unit (nullable, CASCADE) |
| `icon_type` | CharField | `wifi`, `alarm`, `garbage`, `parking`, `electricity`, `water`, `gas`, `intercom`, `laundry`, `other` |
| `label` | CharField(100) | Label |
| `value` | TextField | Value |
| `sort_order` | PositiveSmallIntegerField | Display order (default: 0) |
| `created_at` | DateTimeField | Auto-set |
| `updated_at` | DateTimeField | Auto-updated |

---

### PropertyAgentConfig

AI agent configuration per property.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `property` | OneToOneField → Property | Associated property |
| `maintenance_playbook` | TextField | AI instructions for maintenance |
| `ai_notes` | TextField | Additional context for AI |
| `is_active` | BooleanField | Default: true |
| `updated_at` | DateTimeField | Auto-updated |

---

### PropertyGroup

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `name` | CharField(200) | Group name |
| `description` | TextField | Description |
| `properties` | ManyToManyField → Property | Linked properties |
| `created_at` | DateTimeField | Auto-set |

---

## API Endpoints

All endpoints prefixed with `/api/v1/properties/`.

---

### Properties CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/properties/` | List properties (agents see only theirs) |
| `POST` | `/api/v1/properties/` | Create property (agent auto-set to current user) |
| `GET` | `/api/v1/properties/{id}/` | Retrieve with nested units |
| `PATCH` | `/api/v1/properties/{id}/` | Partial update |
| `PUT` | `/api/v1/properties/{id}/` | Full update |
| `DELETE` | `/api/v1/properties/{id}/` | Delete |

**Auth:** Required for all.

**Create Request:**

```json
{
  "owner": 1,
  "name": "Sunset Apartments",
  "property_type": "apartment",
  "address": "123 Main St",
  "city": "Cape Town",
  "province": "Western Cape",
  "postal_code": "8001",
  "description": "Modern apartment block"
}
```

**List Response:** Paginated. Includes `unit_count` annotation.

**Detail Response:** Includes nested `units` array.

---

### Units CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/properties/units/` | List units |
| `POST` | `/api/v1/properties/units/` | Create unit |
| `GET` | `/api/v1/properties/units/{id}/` | Retrieve |
| `PATCH` | `/api/v1/properties/units/{id}/` | Update |
| `DELETE` | `/api/v1/properties/units/{id}/` | Delete |

**Auth:** Required. **Filters:** `property`, `status`.

**Create Request:**

```json
{
  "property": 1,
  "unit_number": "101",
  "bedrooms": 2,
  "bathrooms": 1,
  "rent_amount": "8500.00",
  "status": "available"
}
```

---

### Unit Info CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/properties/unit-info/` | List info items |
| `POST` | `/api/v1/properties/unit-info/` | Create |
| `GET` | `/api/v1/properties/unit-info/{id}/` | Retrieve |
| `PATCH` | `/api/v1/properties/unit-info/{id}/` | Update |
| `DELETE` | `/api/v1/properties/unit-info/{id}/` | Delete |

**Auth:** Required. **Filters:** `property`, `unit`.

**Create Request:**

```json
{
  "property": 1,
  "unit": 1,
  "icon_type": "wifi",
  "label": "WiFi Password",
  "value": "sunset2026",
  "sort_order": 1
}
```

---

### Property Agent Config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/properties/agent-config/` | List configs |
| `POST` | `/api/v1/properties/agent-config/` | Create |
| `GET` | `/api/v1/properties/agent-config/{id}/` | Retrieve |
| `PATCH` | `/api/v1/properties/agent-config/{id}/` | Update |
| `GET/PATCH` | `/api/v1/properties/agent-config/by-property/{property_id}/` | Get-or-create by property |

**Auth:** Required. **Filter:** `property`.

**Create/Update Request:**

```json
{
  "property": 1,
  "maintenance_playbook": "Always try reset breaker first for electrical issues.",
  "ai_notes": "Building has 3-phase power supply.",
  "is_active": true
}
```

---

### Property Groups

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/properties/groups/` | List groups |
| `POST` | `/api/v1/properties/groups/` | Create group |
| `GET` | `/api/v1/properties/groups/{id}/` | Retrieve with properties |
| `PATCH` | `/api/v1/properties/groups/{id}/` | Update |
| `DELETE` | `/api/v1/properties/groups/{id}/` | Delete |

**Auth:** Required.

**Create Request:**

```json
{
  "name": "CBD Portfolio",
  "description": "All properties in the Cape Town CBD",
  "property_ids": [1, 2, 3]
}
```

**Response:** Includes `property_count`.

---

### Owner Portal

#### Dashboard

```
GET /api/v1/properties/owner/dashboard/
```

**Auth:** Required (user must have `person_profile`)

**Response:** `200 OK`

```json
{
  "total_properties": 3,
  "total_units": 12,
  "occupied_units": 10,
  "occupancy_rate": 83.3,
  "active_issues": 2
}
```

#### Properties List

```
GET /api/v1/properties/owner/properties/
```

**Auth:** Required (user must have `person_profile`)

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "name": "Sunset Apartments",
    "property_type": "apartment",
    "city": "Cape Town",
    "address": "123 Main St",
    "unit_count": 6,
    "occupied_units": 5,
    "active_issues": 1
  }
]
```

---

## Security Notes

| ID | Severity | Issue |
|----|----------|-------|
| VULN-1 | Critical | **IDOR** — Property ViewSet has no ownership filtering. Any user can view/edit/delete any property. |
| VULN-2 | Critical | **IDOR** — Unit ViewSet has no ownership filtering. |
| VULN-3 | Critical | **IDOR** — PropertyAgentConfig ViewSet has no ownership filtering. |
| VULN-21 | Medium | **Negative rent** — No validation preventing negative `rent_amount` on units. |
| VULN-22 | Medium | **Duplicate unit numbers** — No unique constraint on `(property, unit_number)`. |

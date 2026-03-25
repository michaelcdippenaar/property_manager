# Maintenance App

Maintenance request management with supplier dispatch, quoting, AI-assisted matching, agent assist chat, and supplier portal.

## Overview

The maintenance app handles the full repair/maintenance workflow: tenants report issues, agents dispatch jobs to suppliers, suppliers submit quotes (via authenticated portal or anonymous token links), agents award jobs, and activities are tracked in real-time via WebSockets. It also includes an AI agent assist chat with RAG, a maintenance skills knowledge base, and an agent question queue.

---

## Models

### Supplier

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `linked_user` | OneToOneField → User | Portal login (nullable) |
| `name` | CharField(200) | Contact person name |
| `company_name` | CharField(200) | Company name |
| `phone` | CharField(20) | Phone number |
| `email` | EmailField | Email |
| `is_active` | BooleanField | Default: true |
| `address`, `city`, `province` | Various | Address fields |
| `latitude`, `longitude` | DecimalField | Geolocation |
| `service_radius_km` | PositiveIntegerField | Travel radius (nullable) |
| `bee_level`, `cidb_grading` | CharField | SA compliance info |
| `insurance_expiry` | DateField | Nullable |
| `bank_name`, `account_number`, `branch_code`, `account_type` | Various | Banking info |
| `rating` | DecimalField(3,2) | 0-5 rating (nullable) |
| `ai_profile` | JSONField | AI-enriched profile (nullable) |

**Trade choices:** plumbing, electrical, carpentry, painting, roofing, hvac, locksmith, pest_control, landscaping, appliance, general, security, cleaning, other.

### MaintenanceRequest

| Field | Type | Description |
|-------|------|-------------|
| `unit` | ForeignKey → Unit | |
| `tenant` | ForeignKey → User | Reporter |
| `supplier` | ForeignKey → Supplier | Assigned supplier (nullable) |
| `title` | CharField(200) | Issue title |
| `description` | TextField | Detailed description |
| `priority` | CharField | `low`, `medium`, `high`, `urgent` |
| `status` | CharField | `open`, `in_progress`, `resolved`, `closed` |
| `image` | ImageField | Photo (nullable) |

### JobDispatch

| Field | Type | Description |
|-------|------|-------------|
| `maintenance_request` | OneToOneField → MaintenanceRequest | |
| `status` | CharField | `draft`, `sent`, `quoting`, `awarded`, `cancelled` |
| `dispatched_by` | ForeignKey → User | |
| `notes` | TextField | Notes sent to suppliers |

### JobQuoteRequest

| Field | Type | Description |
|-------|------|-------------|
| `dispatch` | ForeignKey → JobDispatch | |
| `supplier` | ForeignKey → Supplier | |
| `status` | CharField | `pending`, `viewed`, `quoted`, `declined`, `awarded`, `expired` |
| `token` | UUIDField | Unique token for anonymous access |
| `match_score` | DecimalField | AI match score (nullable) |
| `match_reasons` | JSONField | Match reasoning (nullable) |

### JobQuote

| Field | Type | Description |
|-------|------|-------------|
| `quote_request` | OneToOneField → JobQuoteRequest | |
| `amount` | DecimalField | Quote amount |
| `description` | TextField | Scope of work |
| `estimated_days` | IntegerField | Duration (nullable) |
| `available_from` | DateField | Start date (nullable) |

### Other Models

- **SupplierTrade** — Junction: Supplier ↔ Trade
- **SupplierDocument** — Compliance documents (bank_confirmation, bee_certificate, insurance, etc.)
- **SupplierProperty** — Links suppliers to properties
- **MaintenanceSkill** — Knowledge base: issue names, trades, difficulty, symptom phrases, resolution steps
- **AgentQuestion** — Questions from AI needing human answers
- **MaintenanceActivity** — Activity log (notes, status changes, etc.)

---

## API Endpoints

All endpoints prefixed with `/api/v1/maintenance/`.

---

### Maintenance Requests

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | List requests (role-filtered). Filters: `status`, `priority`, `unit`, `supplier`, `exclude_status` |
| `POST` | `/` | Create request |
| `GET` | `/{id}/` | Retrieve |
| `PATCH` | `/{id}/` | Update |
| `DELETE` | `/{id}/` | Delete |

---

### Dispatch & Quoting

| Method | Path | Description |
|--------|------|-------------|
| `GET/POST` | `/{id}/dispatch/` | Get or create dispatch (POST includes supplier ranking suggestions) |
| `POST` | `/{id}/dispatch/send/` | Send dispatch to selected suppliers |
| `POST` | `/{id}/dispatch/award/` | Award job to a supplier |

**Send Request:** `{"supplier_ids": [3, 5, 7], "notes": "Urgent job"}`

**Award Request:** `{"quote_request_id": 45}`

---

### Activity

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/{id}/activity/` | List activity log |
| `POST` | `/{id}/activity/` | Add activity note |

---

### Supplier Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/suppliers/` | List (filter: `is_active`) |
| `POST` | `/suppliers/` | Create |
| `GET` | `/suppliers/{id}/` | Detail (full profile with trades, docs, property links) |
| `PATCH` | `/suppliers/{id}/` | Update |
| `DELETE` | `/suppliers/{id}/` | Delete |
| `GET` | `/suppliers/{id}/requests/` | Assigned maintenance requests |
| `GET/POST` | `/suppliers/{id}/documents/` | List/upload documents |
| `DELETE` | `/suppliers/{id}/documents/{doc_id}/` | Delete document |
| `GET/POST` | `/suppliers/{id}/properties/` | List/link properties |
| `DELETE` | `/suppliers/{id}/properties/{link_id}/` | Remove property link |
| `POST` | `/suppliers/{id}/attach_group/` | Attach all properties from a PropertyGroup |
| `POST` | `/suppliers/import_excel/` | Bulk import from Excel |

---

### Token-Based Quote Endpoints (No Auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/quotes/{token}/` | View job details (marks as viewed) |
| `POST` | `/quotes/{token}/` | Submit quote |
| `POST` | `/quotes/{token}/decline/` | Decline job |

**Submit Quote Request:**

```json
{
  "amount": 450.00,
  "description": "Replace tap cartridge",
  "estimated_days": 1,
  "available_from": "2026-03-22"
}
```

---

### Supplier Portal (Authenticated Suppliers)

All require auth + linked `Supplier` profile.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/supplier/dashboard/` | Dashboard stats |
| `GET` | `/supplier/jobs/` | Job list (filter: `?status=...`) |
| `GET` | `/supplier/jobs/{pk}/` | Job detail (marks as viewed) |
| `POST` | `/supplier/jobs/{pk}/quote/` | Submit quote |
| `POST` | `/supplier/jobs/{pk}/decline/` | Decline job |
| `GET/PATCH` | `/supplier/profile/` | View/update profile |
| `GET/POST` | `/supplier/documents/` | List/upload documents |
| `GET` | `/supplier/calendar/` | Calendar of awarded jobs |

**Dashboard Response:**

```json
{
  "new_requests": 3,
  "pending_quotes": 2,
  "awarded_jobs": 1,
  "completed_jobs": 5,
  "rating": 4.5,
  "company_name": "Smith Plumbing"
}
```

---

### Dispatch Overview

```
GET /api/v1/maintenance/dispatches/
```

List all active dispatches with nested quote requests and quotes.

---

### Agent Assist (AI Chat + RAG)

```
POST /api/v1/maintenance/agent-assist/chat/
GET  /api/v1/maintenance/agent-assist/rag-status/
```

**Chat Request:**

```json
{
  "message": "What skills do we have for plumbing?",
  "history": [...],
  "maintenance_request_id": 1
}
```

Uses Claude with RAG over contract documents and maintenance skills knowledge base.

---

### Agent Questions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agent-questions/` | List (filter: `status`, `category`) |
| `POST` | `/agent-questions/` | Create |
| `POST` | `/agent-questions/{id}/answer/` | Answer |
| `POST` | `/agent-questions/{id}/dismiss/` | Dismiss |

---

### Maintenance Skills

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/skills/` | List all (filter: `trade`, `difficulty`, `is_active`, `search`) |
| `POST` | `/skills/` | Create |
| `PATCH` | `/skills/{id}/` | Update |

---

### WebSocket

```
ws://host/ws/maintenance/{maintenance_request_id}/activity/
```

Real-time activity feed. Sends history on connect, broadcasts new activities.

---

## Security Notes

| ID | Severity | Issue |
|----|----------|-------|
| VULN-5 | Critical | **IDOR** — Any authenticated user can CRUD suppliers. No role check. |
| VULN-13 | High | **Token-based AllowAny** — Anyone with a token link can view full job details and submit quotes. Tokens are UUIDs (hard to guess, but no expiration). |

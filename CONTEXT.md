# Klikk — Tremly Property Manager: Project Context

## Overview
Full-stack property management platform for **Klikk (Pty) Ltd** (Tremly). Manages residential rental properties in South Africa. Monorepo with multiple apps:

| App | Stack | URL |
|-----|-------|-----|
| `backend/` | Django 5 + DRF + PostgreSQL + Channels | `http://localhost:8000` |
| `admin/` | Vue 3 + Pinia + TypeScript (multi-role SPA) | `http://localhost:5173` |
| `web_app/` | Vue 3 + TypeScript (tenant portal) | `http://localhost:5174` |
| `tenant_app/` | Flutter (Dart) | iOS/Android |

---

## Running Locally

```bash
# PostgreSQL (Docker or Homebrew)
docker compose up db          # or: brew services start postgresql@15

# Backend
cd backend
source .venv/bin/activate
python manage.py runserver

# Admin SPA (serves agent, supplier, owner portals)
cd admin
npm run dev

# Tenant web app
cd web_app
npm run dev

# Flutter (once SDK installed)
cd tenant_app
flutter run
```

---

## User Roles & Portals

The admin SPA (`/admin`) serves different layouts based on user role:

| Role | Layout | Home Route | Nav Items |
|------|--------|------------|-----------|
| `agent` / `admin` | AgentLayout (top nav + dropdowns) | `/` | Dashboard, Properties, Tenants, Maintenance, Suppliers, Leases, Property Info |
| `supplier` | SupplierLayout | `/jobs` | Jobs, Calendar, Profile |
| `owner` | OwnerLayout | `/owner` | Dashboard, Properties |
| `tenant` | Tenant web app (separate port 5174) | `/` | Home, Issues, Info |

### Test Accounts
- Agent: `mc@tremly.com` / `test1234`
- Supplier: `supplier@test.com` / `test1234` (linked to JvdM Plumbing)
- Tenant: `tenant@test.com`

---

## Backend: Django API

**Base URL:** `http://localhost:8000/api/v1/`

### Auth (`/auth/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register/` | Register new user |
| POST | `/auth/login/` | Login → JWT access + refresh + user (with role) |
| GET | `/auth/me/` | Current user profile |
| POST | `/auth/token/refresh/` | Refresh JWT |
| POST | `/auth/otp/send/` | Send OTP to phone |
| POST | `/auth/otp/verify/` | Verify OTP → returns JWT |
| POST | `/auth/push-token/` | Register FCM push token |
| GET | `/auth/tenants/` | List all tenant users |
| GET/POST | `/auth/persons/` | Person CRUD |

### Properties (`/properties/`)
- CRUD for `Property` and `Unit`
- `GET/POST /properties/groups/` — PropertyGroup CRUD (for bulk supplier assignment)
- `GET /properties/owner/dashboard/` — Owner dashboard stats
- `GET /properties/owner/properties/` — Owner's properties list

### Leases (`/leases/`)
- CRUD for `Lease` with co-tenants, occupants, guarantors
- `GET/POST /leases/{id}/documents/` — upload/list lease documents
- `POST /leases/parse-document/` — AI lease parsing (Claude API)
- `POST /leases/import/` — Import lease from parsed PDF
- Lease templates + builder views

### Maintenance (`/maintenance/`)
- CRUD for `MaintenanceRequest`
- **Supplier management:**
  - `GET/POST /maintenance/suppliers/` — Supplier directory CRUD
  - `GET/POST /maintenance/suppliers/{id}/documents/` — Supplier document uploads
  - `GET/POST /maintenance/suppliers/{id}/properties/` — Link suppliers to properties
  - `POST /maintenance/suppliers/{id}/attach_group/` — Bulk attach PropertyGroup
  - `POST /maintenance/suppliers/import_excel/` — Excel import
- **Job dispatch & quoting:**
  - `POST /maintenance/{id}/dispatch/` — Create dispatch, rank suppliers
  - `POST /maintenance/{id}/dispatch/send/` — Send quote requests to suppliers
  - `POST /maintenance/{id}/dispatch/award/` — Award job to supplier
  - `GET /maintenance/dispatches/` — List all active dispatches
- **Token-based quote pages (no auth):**
  - `GET /maintenance/quotes/{token}/` — Supplier views job details
  - `POST /maintenance/quotes/{token}/` — Submit quote
  - `POST /maintenance/quotes/{token}/decline/` — Decline job
- **Supplier portal (authenticated supplier users):**
  - `GET /maintenance/supplier/dashboard/` — Supplier stats
  - `GET /maintenance/supplier/jobs/` — Quote requests for this supplier
  - `GET /maintenance/supplier/jobs/{id}/` — Job detail
  - `POST /maintenance/supplier/jobs/{id}/quote/` — Submit quote
  - `POST /maintenance/supplier/jobs/{id}/decline/` — Decline job
  - `GET/PATCH /maintenance/supplier/profile/` — Supplier profile
  - `GET/POST /maintenance/supplier/documents/` — Supplier documents
  - `GET /maintenance/supplier/calendar/` — Awarded jobs calendar

### Stats
- `GET /stats/` — Dashboard aggregates (properties, tenants, leases, maintenance, suppliers)

---

## Data Models

### User (accounts)
```
email, first_name, last_name, phone, id_number
role: tenant | agent | admin | supplier | owner
```

### Person (accounts)
```
linked_user → User (optional, for portal login)
person_type: individual | company
full_name, id_number, phone, email, company_reg, vat_number
```

### Property
```
owner → Person, agent → User
name, property_type (apartment|house|townhouse|commercial)
address, city, province, postal_code, description, image
maintenance_playbook (text instructions for agents/AI)
```

### Unit
```
property → Property
unit_number, bedrooms, bathrooms, rent_amount
status: available | occupied | maintenance
floor
```

### PropertyGroup
```
name, description
properties → M2M(Property)
```

### Lease
```
unit → Unit, primary_tenant → Person
start_date, end_date, monthly_rent, deposit
status: active | pending | expired | terminated
lease_number (auto-generated: L-YYYYMM-NNNN)
payment_reference, water/electricity terms, notice period
ai_parse_result (JSON from Claude PDF parsing)
```

### LeaseTenant / LeaseOccupant / LeaseGuarantor / LeaseDocument
Related lease records for co-tenants, occupants, guarantors, and uploaded documents.

### Supplier
```
linked_user → User (optional, for supplier portal login)
name (contact person), company_name, phone, email, website
address, city, province, latitude, longitude, service_radius_km
bee_level, cidb_grading, insurance_expiry, insurance_details
bank_name, account_number, branch_code, account_type
rating (1.0-5.0), ai_profile (JSON for AI matching)
is_active
```

### SupplierTrade
```
supplier → Supplier
trade: plumbing | electrical | carpentry | painting | roofing | hvac | locksmith |
       pest_control | landscaping | appliance | general | security | cleaning | other
```

### SupplierDocument
```
supplier → Supplier
document_type: bank_confirmation | bee_certificate | insurance | cidb |
              company_reg | tax_clearance | other
file, description
```

### SupplierProperty
```
supplier → Supplier, property → Property
is_preferred, notes
```

### MaintenanceRequest
```
unit → Unit, tenant → User, supplier → Supplier (assigned)
title, description
priority: low | medium | high | urgent
status: open | in_progress | resolved | closed
image
```

### JobDispatch
```
maintenance_request → MaintenanceRequest (OneToOne)
status: draft | sent | quoting | awarded | cancelled
dispatched_by → User, dispatched_at, notes
```

### JobQuoteRequest
```
dispatch → JobDispatch, supplier → Supplier
status: pending | viewed | quoted | declined | awarded | expired
token (UUID for tokenised web link)
match_score, match_reasons (JSON breakdown)
notified_at, viewed_at
```

### JobQuote
```
quote_request → JobQuoteRequest (OneToOne)
amount (ZAR), description, estimated_days, available_from
```

---

## Supplier Matching Algorithm

`backend/apps/maintenance/matching.py` — `rank_suppliers(maintenance_request)`

Scores suppliers (0-100) based on weighted factors:
1. **Proximity** (30%) — haversine distance, excluded if outside service_radius_km
2. **Skills match** (25%) — trade alignment with request
3. **Price history** (15%) — average quote vs global average
4. **Owner preference** (20%) — preferred/linked via SupplierProperty
5. **Rating** (10%) — supplier.rating

Returns top N suppliers sorted by score with per-factor breakdown.

---

## Notification Service

`backend/apps/maintenance/notifications.py` — Currently logs to console.

Ready for SMS/WhatsApp integration (Twilio). When a dispatch is sent, each supplier gets a notification with a tokenised link to view and quote on the job.

---

## Vue Admin Views (Agent/Admin)

| Route | View | Data Source |
|-------|------|-------------|
| `/` | Dashboard | `/stats/` + `/maintenance/` |
| `/properties` | Properties list | `/properties/` |
| `/tenants` | Tenants list | `/auth/tenants/` |
| `/maintenance/issues` | Maintenance board (two-column: list + detail panel) | `/maintenance/` |
| `/maintenance/suppliers` | Suppliers in maintenance context | `/maintenance/` |
| `/maintenance/ai-questions` | AI agent pending questions | `/maintenance/` |
| `/maintenance/ai-sandbox` | Staff AI assistant | `/maintenance/` |
| `/suppliers` | Supplier directory (table + detail slide-over) | `/maintenance/suppliers/` |
| `/suppliers/dispatch` | Dispatch overview + quote comparison | `/maintenance/dispatches/` |
| `/leases` | Leases + import from PDF | `/leases/` |
| `/leases/build` | Lease builder | `/leases/` |
| `/property-info/agent` | Agent context config | |
| `/property-info/skills` | Maintenance skill library | |
| `/property-info/unit-info` | Unit tenant info | |

## Vue Supplier Views

| Route | View | Data Source |
|-------|------|-------------|
| `/jobs` | Jobs list + stats + detail panel with quote form | `/maintenance/supplier/jobs/` |
| `/calendar` | Monthly calendar with awarded jobs | `/maintenance/supplier/calendar/` |
| `/profile` | Profile editor (company, trades, banking, docs) | `/maintenance/supplier/profile/` |

## Vue Owner Views

| Route | View | Data Source |
|-------|------|-------------|
| `/owner` | Dashboard (properties, occupancy, issues) | `/properties/owner/dashboard/` |
| `/owner/properties` | Owned properties list | `/properties/owner/properties/` |

---

## Design System
- **Primary navy:** `#2B2D6E`
- **Accent pink:** `#FF3D7F`
- **Splash background:** `#F0EFF8`
- **Font:** Inter
- **Figma file:** `SNhM6RTJf0mqTy0ELbCbFi`

---

## Key Integrations
- **Claude AI** — Lease PDF parsing, maintenance triage, staff assistant
- **DocuSeal** — E-signing (backend complete, UI in progress)
- **Google Maps** — Address geocoding, supplier proximity matching
- **openpyxl** — Excel import for bulk supplier creation
- **Twilio** (planned) — SMS/WhatsApp notifications for supplier dispatch
- **Firebase** (planned) — Push notifications

---

## Key Business Rules
- Up to 4 tenants per property unit
- Each tenant can have a guardian/co-debtor
- Water included up to 4,000 litres/month per occupant
- Electricity via prepaid meter (tenant pays directly)
- Deposit = 1 month rent (standard)
- Early termination: 20 business days notice, up to 3 months penalty
- Payment references per tenant: `"<Property> - <Surname>"`
- Landlord: Klikk (Pty) Ltd, reg 2016/113758/07

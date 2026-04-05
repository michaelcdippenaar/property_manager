# System Architecture

Concise technical reference for AI agents writing tests. For the full narrative see
`/Users/mcdippenaar/PycharmProjects/tremly_property_manager/CONTEXT.md`.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 5 + Django REST Framework |
| Database | PostgreSQL 15 |
| Async / WebSocket | Django Channels + Daphne (ASGI) |
| Auth | JWT via `djangorestframework-simplejwt` |
| Task queue | (Celery not yet wired — background work is synchronous or via management commands) |
| PDF generation | Gotenberg (Docker sidecar, `http://localhost:3000`) |
| E-signing | DocuSeal (self-hosted or cloud API) |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |
| Push notifications | Firebase Admin SDK (FCM) |
| Tests | pytest + pytest-django + DRF APITestCase |

**API base URL:** `http://localhost:8000/api/v1/`

---

## Django Apps

| App | Path | Responsibility |
|-----|------|---------------|
| `accounts` | `apps/accounts/` | User model, auth (JWT + OTP + OAuth), roles, permissions, Person profile, audit log |
| `properties` | `apps/properties/` | Property and Unit CRUD, landlord/banking records, owner dashboard, access control |
| `leases` | `apps/leases/` | Lease agreements, templates (TipTap HTML), AI-assisted builder, reusable clauses, events |
| `maintenance` | `apps/maintenance/` | Maintenance requests, supplier directory, job dispatch, quote flow, AI agent assist |
| `esigning` | `apps/esigning/` | DocuSeal e-signing, Gotenberg PDF, audit trail, native signing, public links |
| `ai` | `apps/ai/` | Tenant intelligence, lease parsing, skills registry, training utilities |
| `tenant_portal` | `apps/tenant_portal/` | Tenant-facing AI chat, maintenance ticket creation from chat, heuristic classifiers |
| `notifications` | `apps/notifications/` | Push (Firebase) and email notification dispatch |
| `test_hub` | `apps/test_hub/` | Test infrastructure — base class, factories, context docs, management commands |

---

## Authentication

- **Mechanism:** JWT (access token + refresh token)
- **Access token lifetime:** short (minutes) — configured in `SIMPLE_JWT` settings
- **Refresh token lifetime:** longer (days)
- **Custom User model:** `accounts.User` (extends `AbstractBaseUser`)
- **USERNAME_FIELD:** `email` (not username)
- **Login endpoint:** `POST /api/v1/auth/login/` → returns `{access, refresh, user}`
- **Refresh endpoint:** `POST /api/v1/auth/token/refresh/`
- **OTP endpoint:** `POST /api/v1/auth/otp/send/` + `POST /api/v1/auth/otp/verify/`

---

## User Roles

Five roles are hard-coded as `TextChoices` on `accounts.User.Role`:

| Role | Value | Portal / Access |
|------|-------|----------------|
| `admin` | `"admin"` | Full access to all resources via Django admin + agent portal |
| `agent` | `"agent"` | Agent portal — manages properties, leases, maintenance, suppliers |
| `tenant` | `"tenant"` | Tenant web app + Flutter app — chat, issues, lease info |
| `supplier` | `"supplier"` | Supplier portal — view dispatched jobs, submit quotes |
| `owner` | `"owner"` | Owner portal — read-only view of own properties/financials |

---

## Permission Classes (`apps/accounts/permissions.py`)

| Class | Allows |
|-------|--------|
| `IsAdmin` | role == admin |
| `IsAgentOrAdmin` | role in (agent, admin) |
| `IsOwner` | role == owner |
| `IsOwnerOrStaff` | role in (owner, agent, admin) |
| `IsSupplier` | role == supplier |
| `IsTenant` | role == tenant |

---

## Key Integrations

### DocuSeal (E-signing)
- Self-hosted or cloud SaaS
- HTML-based templates with `data-*` field tags
- Webhooks for signing status updates (HMAC-validated)
- Wrapped by `apps/esigning/services.py`

### Gotenberg (PDF)
- Docker sidecar at `http://localhost:3000`
- Accepts HTML → returns PDF bytes
- Used for lease PDF rendering and signed PDF assembly
- Wrapped by `apps/esigning/gotenberg.py`

### Firebase (Push)
- Firebase Admin SDK
- Device tokens stored in `accounts.PushToken`
- Dispatch via `apps/notifications/services.py`

### Anthropic Claude API
- Model: `claude-sonnet-4-6`
- Used for: lease PDF parsing, maintenance triage, tenant chat, staff assistant
- Skills/tools defined in `apps/ai/skills_registry.py`

---

## South African Context

| Concept | Detail |
|---------|--------|
| Privacy law | POPIA (Protection of Personal Information Act) — governs data handling |
| Tenancy law | RHA (Rental Housing Act) — mandatory lease clauses, notice periods |
| Currency | ZAR (South African Rand) — all monetary values |
| ID numbers | SA ID (13-digit) or passport |
| Deposit standard | 1 month's rent |
| Notice period | Typically 20 business days under RHA |
| Landlord entity | Klikk (Pty) Ltd, reg 2016/113758/07 |

---

## Business Rules Relevant to Tests

- Up to 4 tenants per unit
- Electricity via prepaid meter (tenant responsibility)
- Water included up to 4,000 litres/month per occupant
- Early termination: 20 business days notice, up to 3 months penalty
- Lease number auto-generated: `L-YYYYMM-NNNN`
- Payment reference: `"<Property> - <Surname>"`

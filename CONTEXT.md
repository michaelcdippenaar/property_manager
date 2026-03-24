# Klikk — Tremly Property Manager: Project Context

## Overview
Full-stack property management platform for **Klikk (Pty) Ltd** (Tremly). Manages residential rental properties in South Africa. Three apps in a monorepo:

| App | Stack | URL |
|-----|-------|-----|
| `backend/` | Django 5 + DRF + PostgreSQL | `http://localhost:8000` |
| `admin/` | Vue 3 + Vuetify 3 + Pinia + TypeScript | `http://localhost:5173` |
| `mobile/` | Flutter (Dart) | iOS/Android |

---

## Running Locally

```bash
# PostgreSQL (Homebrew)
brew services start postgresql@15

# Backend
cd backend
source .venv/bin/activate
python manage.py runserver

# Admin
cd admin
npm run dev

# Flutter (once SDK installed)
cd mobile
flutter run
```

---

## Backend: Django API

**Base URL:** `http://localhost:8000/api/v1/`

### Auth (`/auth/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register/` | Register new user |
| POST | `/auth/login/` | Login → returns JWT access + refresh |
| GET | `/auth/me/` | Current user profile |
| POST | `/auth/token/refresh/` | Refresh JWT |
| POST | `/auth/otp/send/` | Send OTP to phone |
| POST | `/auth/otp/verify/` | Verify OTP → returns JWT |
| GET | `/auth/tenants/` | List all tenant users |

### Properties (`/properties/`)
- CRUD for `Property` and `Unit`
- `GET /properties/units/` — list all units

### Leases (`/leases/`)
- CRUD for `Lease`
- `GET/POST /leases/{id}/documents/` — list or upload documents to a lease

### Maintenance (`/maintenance/`)
- CRUD for `MaintenanceRequest`

### Stats
- `GET /stats/` — dashboard aggregate counts

---

## Data Models

### User (accounts)
```
email, first_name, last_name, phone, id_number, role (tenant|agent|admin)
```

### Property
```
name, property_type, address, city, province, postal_code, description, image
agent → User
```

### Unit
```
unit_number, bedrooms, bathrooms, rent_amount, status (available|occupied|maintenance), floor
property → Property
```

### Lease
```
tenant → User, unit → Unit
start_date, end_date, monthly_rent, deposit, status (active|pending|expired|terminated)
max_occupants, water_included, water_limit_litres, electricity_prepaid
notice_period_days, early_termination_penalty_months
payment_reference (e.g. "18 Irene - Smith")
```

### Guardian (co-debtor on a lease)
```
lease → Lease, tenant → User
full_name, id_number, phone, email
```

### LeaseDocument
```
lease → Lease
document_type (signed_lease|id_copy|other)
file (uploaded PDF/image)
description, uploaded_by → User
```

### MaintenanceRequest
```
unit → Unit, tenant → User
title, description, priority (low|medium|high|urgent), status (open|in_progress|resolved|closed)
image
```

---

## Vue Admin Views

| Route | View | Data Source |
|-------|------|-------------|
| `/` | Dashboard | `/api/v1/stats/` + `/api/v1/maintenance/` |
| `/properties` | Properties list | `/api/v1/properties/` |
| `/tenants` | Tenants list | `/api/v1/auth/tenants/` |
| `/maintenance` | Maintenance board | `/api/v1/maintenance/` |
| `/leases` | Leases + document upload | `/api/v1/leases/` |

---

## Flutter Mobile (Klikk Tenant App)

**Status:** Source files written, Flutter SDK needs to be installed.

### Auth Screens Built
- Splash → Login Email → Login Mobile → OTP → Sign Up

### Key Files
```
mobile/lib/
  main.dart               — app entry, MaterialApp.router
  theme/app_colors.dart   — #2B2D6E (navy), #FF3D7F (pink), #F0EFF8 (splash bg)
  theme/app_theme.dart    — ThemeData
  router/app_router.dart  — go_router routes
  widgets/                — KlikkLogo, AuthHeader, AuthCard, PrimaryButton, inputs
  screens/auth/           — all auth screens
```

### Install Flutter
```bash
brew install flutter
cd mobile && flutter pub get && flutter run
```

---

## Design System (Figma)
- **File:** `SNhM6RTJf0mqTy0ELbCbFi` (Klikk team library)
- **Primary navy:** `#2B2D6E`
- **Accent pink:** `#FF3D7F`
- **Splash background:** `#F0EFF8`
- **Font:** Inter

---

## Key Business Rules (from real lease contracts)
- Up to 4 tenants per property unit
- Each tenant can have a guardian/co-debtor
- Water included up to 4,000 litres/month per occupant
- Electricity via prepaid meter (tenant pays directly)
- Deposit = 1 month rent (standard)
- Early termination: 20 business days notice, up to 3 months penalty
- Payment references per tenant: `"<Property> - <Surname>"`
- Landlord: Klikk (Pty) Ltd, reg 2016/113758/07

---

## TODO / Next Steps
- [ ] Install Flutter SDK + wire mobile auth to real API
- [ ] Add AI lease parsing (Claude API) — read uploaded PDFs and auto-fill lease fields
- [ ] SMS OTP integration (Africa's Talking or Twilio)
- [ ] Seed real property data from Google Drive
- [ ] Django admin registration for all models
- [ ] Production deployment (gunicorn + nginx + certbot)

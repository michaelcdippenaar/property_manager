# Test Structure, Factory Methods & Commands

---

## Directory Layout

```
backend/apps/test_hub/
├── base/
│   └── test_case.py          ← TremlyAPITestCase — all factory methods live here
├── context/                  ← AI-readable markdown (vectorised into ChromaDB)
│   ├── README.md
│   ├── architecture.md
│   ├── tdd_workflow.md
│   ├── bug_workflow.md
│   ├── conventions.md
│   └── modules/<module>.md   ← per-module domain context + coverage gaps
├── issues/<module>/          ← Bug history (also vectorised)
└── <module>/
    ├── conftest.py            ← module-specific fixtures
    ├── unit/                  ← no DB, fast, isolated
    └── integration/           ← full Django stack + API client
```

**Two tiers per module:**
- `unit/` — models, serializers, permissions, utils, signals in isolation
- `integration/` — API endpoints via DRF test client with real DB

All test classes inherit from `TremlyAPITestCase` or use the `tremly` pytest fixture.

---

## Factory Methods

```python
from apps.test_hub.base.test_case import TremlyAPITestCase

class TestFoo(TremlyAPITestCase):
    # User factories
    user   = self.create_user(email=..., role=...)
    admin  = self.create_admin()
    agent  = self.create_agent()
    tenant = self.create_tenant()
    sup    = self.create_supplier_user()
    owner  = self.create_owner_user()

    # Data factories
    person   = self.create_person(full_name="Jane Doe", linked_user=user)
    prop     = self.create_property(agent=agent)
    unit     = self.create_unit(property_obj=prop)
    lease    = self.create_lease(unit=unit, primary_tenant=tenant)
    request  = self.create_maintenance_request(unit=unit, tenant=tenant)
    supplier = self.create_supplier()

    # Auth helpers
    self.authenticate(user)          # force-auth the test client
    tokens = self.get_tokens(user)   # returns {access, refresh}
```

**Pytest fixture equivalent** (`conftest.py` provides `tremly`):

```python
def test_something(tremly):
    agent  = tremly.create_agent()
    tenant = tremly.create_tenant()
    tremly.authenticate(agent)
    ...
```

---

## Pytest Commands

```bash
cd backend

# By TDD phase
pytest -m red                                # All pending (must xfail)
pytest -m green                              # All passing
pytest -m unit                               # Fast unit tests only
pytest -m integration                        # API-level tests

# By module
pytest apps/test_hub/accounts/
pytest apps/test_hub/leases/
pytest apps/test_hub/maintenance/
pytest apps/test_hub/esigning/
pytest apps/test_hub/properties/
pytest apps/test_hub/ai/
pytest apps/test_hub/tenant_portal/

# TDD cycle report
python manage.py run_tdd --cycle
python manage.py run_tdd --module leases

# Coverage
pytest --cov=apps --cov-report=term-missing

# Deduplication check
pytest --co -q | grep -i <keyword>
```

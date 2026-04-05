# TDD Workflow — Red-Green-Refactor

This document defines the mandatory TDD workflow for all tests in the Tremly test suite.
Every AI agent writing tests MUST follow this workflow without exception.

---

## The Three Phases

### Phase 1: Red — Write a Failing Test First

Before any implementation exists, write a test that describes the desired behaviour.
The test MUST fail when run. This proves the test is actually exercising real code and
not passing vacuously.

Mark the test with `@pytest.mark.red`. The conftest.py enforces `xfail(strict=True)` on
all red-marked tests, which means:
- If the test fails (as expected) → pytest reports `XFAIL` (expected failure — OK)
- If the test passes (implementation already exists) → pytest reports `XPASS` and **fails the suite**

This prevents accidentally green tests from being labelled red.

### Phase 2: Green — Implement Until the Test Passes

Write the minimum implementation needed to make the red test pass.
Remove `@pytest.mark.red` and add `@pytest.mark.green`.
Run the test. It must now pass (`PASSED`).

Do not over-engineer at this stage. Only write enough code to satisfy the test.

### Phase 3: Refactor — Improve Without Changing Behaviour

Improve the implementation — extract methods, rename variables, reduce duplication.
All `@pytest.mark.green` tests must continue passing after every refactor step.
No new behaviour is introduced during refactor.

---

## Pytest Marker System

Markers are registered globally in `pytest.ini` / `pyproject.toml` and enforced in
`backend/conftest.py`.

| Marker | Meaning | conftest behaviour |
|--------|---------|-------------------|
| `@pytest.mark.red` | Test not yet passing — implementation not written | `xfail(strict=True)` automatically applied |
| `@pytest.mark.green` | Test passes — implementation complete | Normal pass expected |
| `@pytest.mark.refactor` | Refactor in progress — behaviour unchanged | Normal pass expected |
| `@pytest.mark.unit` | No database, no external services, fast | No special enforcement |
| `@pytest.mark.integration` | Uses DB and/or API client | No special enforcement |
| `@pytest.mark.e2e` | Full stack end-to-end (Playwright or MCP) | No special enforcement |

### Applying markers

At module level (applies to all tests in the file):

```python
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]
```

Per class:

```python
@pytest.mark.unit
class TestMySerializer:
    ...
```

Per test function:

```python
@pytest.mark.red
def test_user_cannot_register_with_duplicate_email(self):
    ...
```

---

## conftest.py Enforcement

`backend/conftest.py` contains the following hook:

```python
def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("red"):
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    reason="RED: implementation not written yet — this test must fail",
                )
            )
```

This runs at collection time. You do not need to add `xfail` yourself — just add
`@pytest.mark.red` and the conftest handles enforcement.

---

## Step-by-Step AI Agent Workflow

### Step 1: Read the module context

```
Read context/modules/<module>.md before writing any tests.
Understand: models, key invariants, integration dependencies, known coverage gaps.
```

### Step 2: Write the red test

```python
# apps/test_hub/accounts/test_registration.py
import pytest
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.red]


class TestUserRegistration(TremlyAPITestCase):

    @pytest.mark.red
    def test_duplicate_email_returns_400(self):
        self.create_user(email="dup@test.com")
        response = self.client.post("/api/v1/auth/register/", {
            "email": "dup@test.com",
            "password": "testpass123",
            "role": "tenant",
        })
        assert response.status_code == 400
        assert "email" in response.data
```

### Step 3: Confirm it xfails

```bash
cd backend
pytest apps/test_hub/accounts/test_registration.py -v
# Expected output: XFAIL test_duplicate_email_returns_400
```

### Step 4: Implement the feature

Write the minimum view / serializer / model change to make the test pass.

### Step 5: Transition red → green

```python
# Remove @pytest.mark.red, add @pytest.mark.green
pytestmark = [pytest.mark.integration, pytest.mark.green]
```

### Step 6: Confirm it passes

```bash
pytest apps/test_hub/accounts/test_registration.py -v
# Expected output: PASSED test_duplicate_email_returns_400
```

### Step 7: Refactor if needed

```python
pytestmark = [pytest.mark.integration, pytest.mark.green, pytest.mark.refactor]
```

Run the full module suite to verify nothing regressed:

```bash
pytest apps/test_hub/accounts/ -v
```

---

## Rules

1. Never write implementation code without a corresponding red test.
2. Red tests must truly fail — if a test passes when marked red, the conftest will fail the suite.
3. Never mark a test green until it actually passes.
4. Refactor only after all relevant tests are green.
5. Do not introduce new behaviour during the refactor phase.
6. Each test must assert exactly one logical behaviour (one reason to fail).

---

## Examples

### Model test (unit — no DB)

```python
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestUnitModel:

    def test_rent_amount_is_decimal(self):
        unit = MagicMock()
        unit.rent_amount = Decimal("5000.00")
        assert isinstance(unit.rent_amount, Decimal)
```

### Serializer test (unit)

```python
import pytest
from apps.accounts.serializers import UserSerializer

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestUserSerializer:

    def test_password_not_in_serialized_output(self):
        data = {"email": "a@test.com", "role": "tenant", "password": "secret"}
        serializer = UserSerializer(data=data)
        serializer.is_valid()
        assert "password" not in serializer.data
```

### Permission test (integration)

```python
import pytest
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class TestIsAgentOrAdminPermission(TremlyAPITestCase):

    def test_tenant_cannot_list_suppliers(self):
        tenant = self.create_tenant()
        self.authenticate(tenant)
        response = self.client.get("/api/v1/maintenance/suppliers/")
        assert response.status_code == 403

    def test_agent_can_list_suppliers(self):
        agent = self.create_agent()
        self.authenticate(agent)
        response = self.client.get("/api/v1/maintenance/suppliers/")
        assert response.status_code == 200
```

### Service / utility test (unit with mock)

```python
import pytest
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestDocuSealService:

    @patch("apps.esigning.services.requests.post")
    def test_create_submission_posts_to_docuseal(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"id": 42})
        from apps.esigning.services import create_submission
        result = create_submission(template_id=1, signers=[])
        assert result["id"] == 42
        mock_post.assert_called_once()
```

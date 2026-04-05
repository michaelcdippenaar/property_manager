# Test Conventions

This document defines naming conventions, import patterns, factory usage, mock strategies,
and run commands for the Tremly test suite. Read this before writing any test file.

---

## Import Pattern

All test files import the shared base class:

```python
from apps.test_hub.base.test_case import TremlyAPITestCase
```

This is the single source of truth for all factory methods. Never create models directly
in test files using `Model.objects.create(...)` unless `TremlyAPITestCase` does not provide
a factory for that model.

---

## Pytest Marker Usage

### Module-level (preferred — applies to every test in the file)

```python
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]
```

### Class-level (when a file mixes unit and integration tests)

```python
@pytest.mark.unit
class TestMySerializer:
    ...

@pytest.mark.integration
class TestMyView(TremlyAPITestCase):
    ...
```

### Function-level (for a single test with a different phase marker)

```python
@pytest.mark.red
def test_feature_not_yet_built(self):
    ...
```

---

## TremlyAPITestCase Factory Methods

All factory methods accept `**kwargs` to override defaults.

### User factories

```python
# Generic
user = self.create_user(email="u@test.com", password="pass123", role="tenant")

# Role shortcuts
admin   = self.create_admin(email="admin@test.com")
agent   = self.create_agent(email="agent@test.com")
tenant  = self.create_tenant(email="tenant@test.com")
supplier_user = self.create_supplier_user(email="sup@test.com")
owner_user    = self.create_owner_user(email="owner@test.com")
```

### Person factory

```python
person = self.create_person(full_name="Jane Doe", linked_user=tenant)
# Without linked user (e.g. guarantor who has no portal login)
guarantor = self.create_person(full_name="John Guarantor")
```

### Property and Unit factories

```python
prop = self.create_property(agent=agent, name="Sea Point Apartments")
# Defaults: property_type="apartment", city="Cape Town", province="Western Cape"

unit = self.create_unit(property_obj=prop, unit_number="2A")
# Defaults: bedrooms=1, bathrooms=1, rent_amount=Decimal("5000.00"), status="available"
# If property_obj is None, a new property is auto-created
```

### Lease factory

```python
lease = self.create_lease(unit=unit, primary_tenant=person)
# Defaults: start_date=today, end_date=today+365d, monthly_rent=5000, deposit=10000, status="active"
# primary_tenant accepts a Person instance (not User)
```

### Maintenance factories

```python
mr = self.create_maintenance_request(unit=unit, tenant=tenant)
# Defaults: title="Leaking tap", priority="medium", status="open"
# tenant is a User with role="tenant"

supplier = self.create_supplier(name="JvdM Plumbing", phone="0821234567")
# Add keyword overrides: city="Cape Town", latitude=-33.9, longitude=18.4
```

### Auth helpers

```python
# Force-authenticate the test client (no real JWT exchange — fastest for integration tests)
self.authenticate(user)

# Get real JWT tokens (use when testing token-based flows)
tokens = self.get_tokens(user)
# Returns: {"access": "...", "refresh": "..."}
self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
```

---

## Authentication in Integration Tests

Prefer `self.authenticate(user)` for most integration tests — it skips the JWT exchange
and directly sets the authenticated user on the client.

Use `self.get_tokens(user)` only when testing JWT-specific behaviour (token expiry,
refresh, token contents, etc.).

```python
class TestLeaseView(TremlyAPITestCase):

    def test_agent_can_create_lease(self):
        agent = self.create_agent()
        self.authenticate(agent)          # fast path
        unit = self.create_unit()
        response = self.client.post("/api/v1/leases/", {...})
        assert response.status_code == 201

    def test_jwt_refresh_returns_new_access_token(self):
        tenant = self.create_tenant()
        tokens = self.get_tokens(tenant)  # real JWT needed
        response = self.client.post("/api/v1/auth/token/refresh/", {
            "refresh": tokens["refresh"]
        })
        assert response.status_code == 200
        assert "access" in response.data
```

---

## Mock Patterns for External Services

### DocuSeal API

```python
from unittest.mock import patch, MagicMock

@patch("apps.esigning.services.requests.post")
def test_submission_created(self, mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"id": 99, "status": "pending"}
    )
    # call your view or service
```

### Gotenberg PDF service

```python
@patch("apps.esigning.gotenberg.requests.post")
def test_pdf_generated(self, mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        content=b"%PDF-1.4 fake content",
        headers={"Content-Type": "application/pdf"},
    )
```

### Firebase push notifications

```python
@patch("apps.notifications.services.messaging.send")
def test_push_sent_to_tenant(self, mock_send):
    mock_send.return_value = "projects/tremly/messages/abc123"
    # trigger the notification
    mock_send.assert_called_once()
```

### Anthropic Claude API

```python
@patch("apps.ai.parsing.anthropic.Anthropic")
def test_parse_returns_structured_data(self, MockClient):
    mock_client = MagicMock()
    MockClient.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"trade": "plumbing", "urgency": "medium"}')]
    )
    from apps.ai.parsing import parse_maintenance_draft_response
    result = parse_maintenance_draft_response("tap is leaking")
    assert result["trade"] == "plumbing"
```

---

## File Upload Testing

Use `django.core.files.uploadedfile.SimpleUploadedFile`:

```python
from django.core.files.uploadedfile import SimpleUploadedFile

def test_supplier_document_upload(self):
    agent = self.create_agent()
    self.authenticate(agent)
    supplier = self.create_supplier()
    pdf = SimpleUploadedFile("insurance.pdf", b"%PDF fake", content_type="application/pdf")
    response = self.client.post(
        f"/api/v1/maintenance/suppliers/{supplier.id}/documents/",
        {"document_type": "insurance", "file": pdf},
        format="multipart",
    )
    assert response.status_code == 201
```

---

## Naming Conventions

Test files, classes, and methods follow these patterns:

| What | Pattern | Example |
|------|---------|---------|
| Test file | `test_<subject>.py` | `test_registration.py` |
| Model test class | `TestXxxModel` | `TestUserModel` |
| Serializer test class | `TestXxxSerializer` | `TestLeaseSerializer` |
| Permission test class | `TestXxxPermission` | `TestIsAgentOrAdminPermission` |
| View/endpoint test class | `TestXxxView` or `TestXxxEndpoint` | `TestLeaseCreateView` |
| Service/utility test class | `TestXxxService` | `TestDocuSealService` |
| Test method | `test_<condition>_<expected_outcome>` | `test_duplicate_email_returns_400` |

Keep test method names specific enough to be self-documenting:
- `test_tenant_cannot_access_supplier_endpoint` (not `test_permission`)
- `test_lease_end_date_must_be_after_start_date` (not `test_validation`)

---

## Running Tests

```bash
# All tests
cd backend
pytest apps/test_hub/

# One module
pytest apps/test_hub/accounts/

# By marker
pytest -m unit
pytest -m integration
pytest -m green
pytest -m "green and unit"

# Verbose with short TB
pytest apps/test_hub/ -v --tb=short

# Stop on first failure
pytest apps/test_hub/ -x

# Run only red tests (check they xfail)
pytest -m red -v
```

---

## pytest Fixture Shortcuts (from conftest.py)

The root `backend/conftest.py` provides fixtures for common objects:

```python
def test_something(api_client, agent_user, tenant_user):
    api_client.force_authenticate(user=agent_user)
    ...

def test_with_tremly_factory(tremly):
    prop = tremly.create_property()
    unit = tremly.create_unit(property_obj=prop)
    ...
```

Available fixtures: `api_client`, `tremly`, `admin_user`, `agent_user`,
`tenant_user`, `supplier_user`, `owner_user`.

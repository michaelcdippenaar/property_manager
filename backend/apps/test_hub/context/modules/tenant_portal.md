# Module: tenant_portal

**App path:** `apps/tenant_portal/`
**Domain:** Tenant-facing AI chat interface, maintenance ticket creation from chat, heuristic classifiers, rate limiting.

---

## Models

The tenant portal has no models of its own. It uses:
- `apps.ai.TenantChatSession` — stores chat sessions
- `apps.maintenance.MaintenanceRequest` — tickets created from chat
- `apps.accounts.User` — authenticated tenant user

---

## Key Functions in `views.py`

### Heuristic Classifiers

| Function | Purpose |
|----------|---------|
| `_heuristic_maintenance_ticket(message)` | Returns `True` if the message is likely a maintenance request. Uses keyword matching and pattern rules (no AI call). |
| `_heuristic_severe_ticket(message)` | Returns `True` if the message indicates urgent/severe issue (e.g. flooding, gas leak, no power). |

These are fast, deterministic functions. They run before the AI call to decide whether
to trigger maintenance ticket creation and what priority to assign.

Test with: known maintenance phrases → True; non-maintenance phrases → False.

### Session Helpers

| Function | Purpose |
|----------|---------|
| `_session_for_user(user)` | Gets or creates the active `TenantChatSession` for the tenant |
| `_maybe_update_session_title(session, message)` | If session has no title, generates one from the first message (truncated) |

### Message Handling

| Function | Purpose |
|----------|---------|
| `_serialize_stored_message(msg)` | Converts a stored message dict to API response format |
| `_build_windowed_messages(session, window_size=20)` | Returns the last N messages from session history as Anthropic-formatted message list |

`_build_windowed_messages` ensures Claude never receives more than `window_size` messages,
preventing context overflow. It must preserve message order (oldest first).

### Maintenance Ticket Creation

| Function | Purpose |
|----------|---------|
| `_create_mr_from_chat(tenant, unit, title, description, priority)` | Creates a `MaintenanceRequest` from chat context |
| `_ensure_truthful_maintenance_reply(response, maintenance_request)` | Validates that the AI reply is consistent with the created ticket (no hallucinated ticket details) |

### Chat Endpoint Flow

```
POST /api/v1/tenant-portal/chat/
  1. Authenticate tenant (IsTenant permission)
  2. Rate limit check (TenantChatThrottle)
  3. Get/create session (_session_for_user)
  4. _heuristic_maintenance_ticket → if True, pre-classify
  5. _heuristic_severe_ticket → set priority=urgent if True
  6. _build_windowed_messages → prepare context
  7. Call Claude (apps.ai skills + tenant context)
  8. Parse response (apps.ai.parsing)
  9. If AI decides to create ticket → _create_mr_from_chat
  10. _ensure_truthful_maintenance_reply
  11. Store message + response in session
  12. _maybe_update_session_title
  13. Return serialized response
```

---

## Throttles

| Throttle class | Applied to | Rate |
|----------------|-----------|------|
| `TenantChatThrottle` | `POST /chat/` | N messages per minute (configured in settings) |
| `TenantDraftThrottle` | `POST /draft/` | Lower rate for draft generation |

In tests, disable throttling by overriding `DEFAULT_THROTTLE_CLASSES = []` in test settings,
or use `override_settings`:

```python
from django.test import override_settings

@override_settings(DEFAULT_THROTTLE_CLASSES=[], DEFAULT_THROTTLE_RATES={})
def test_chat_returns_ai_response(self):
    ...
```

---

## Rate Limiting Behaviour

When throttled, the endpoint returns `429 Too Many Requests`.
Test this by sending rapid successive requests (or mocking the throttle cache).

---

## API Endpoints

```
POST /api/v1/tenant-portal/chat/        — Send a chat message, get AI response
GET  /api/v1/tenant-portal/chat/        — List chat history for current session
POST /api/v1/tenant-portal/draft/       — Draft a maintenance message (lower rate limit)
GET  /api/v1/tenant-portal/sessions/    — List chat sessions for tenant
```

All endpoints require `IsTenant` permission. Non-tenant roles must receive 403.

---

## Key Invariants

- Chat messages must be stored in chronological order (oldest first in session)
- A session belongs to exactly one tenant; sessions cannot be shared
- The windowed message builder must not exceed `window_size` messages
- Maintenance tickets created from chat must reference the tenant's current unit
- If no active lease/unit found for tenant, chat still works but cannot create tickets
- `_ensure_truthful_maintenance_reply` must reject responses that reference a ticket ID not matching the created one

---

## Integration Dependencies

- **Anthropic Claude API** — chat completion (mock in tests)
- `apps.ai` — `TenantChatSession`, `build_tenant_context`, `parse_tenant_ai_response`
- `apps.maintenance` — `MaintenanceRequest` creation
- `apps.leases` — to find tenant's active unit

---

## Known Test Areas

- `_heuristic_maintenance_ticket("tap is leaking")` → True
- `_heuristic_maintenance_ticket("what time is checkout?")` → False
- `_heuristic_severe_ticket("flooding in bathroom")` → True
- `_heuristic_severe_ticket("tap dripping slightly")` → False
- Chat: unauthenticated request → 401
- Chat: tenant without active lease → 200 (no ticket created)
- Chat: maintenance message → ticket created → 201 ticket in DB
- Chat: non-maintenance message → no ticket created
- Session: get or create on first message
- Session title: set from first message if blank
- Windowed messages: only last N messages returned

---

## Coverage Gaps

- `_heuristic_maintenance_ticket` unit tests with edge cases (mixed signals, short messages)
- `_build_windowed_messages` with exactly N, N-1, N+1 messages
- `_ensure_truthful_maintenance_reply` rejection cases
- Throttle tests: verify 429 after rate limit exceeded
- Session isolation: tenant A cannot read tenant B's session
- Draft endpoint tests

# Module: ai

**App path:** `apps/ai/`
**Domain:** AI-powered features — lease parsing, tenant intelligence, skills/tools registry, tenant context assembly, training utilities.

---

## Models

| Model | Key Fields |
|-------|-----------|
| `TenantChatSession` | `tenant` (FK→User), `title` (auto-generated), `created_at`, `updated_at`. Stores the conversation session; individual messages stored as JSONL or in a related model. |
| `TenantIntelligence` | `tenant` (FK→User, OneToOne), `facts` (JSON — extracted facts about the tenant), `last_updated`, `classification` (JSON — risk/behaviour classification) |

---

## Key Utilities

### `intel.py` — `update_tenant_intel(tenant_user)`

Reads recent chat history for the tenant and calls Claude to:
- Classify tenant behaviour (e.g. `payment_risk`, `communication_style`)
- Extract structured facts (employer, pets, maintenance patterns)

Updates `TenantIntelligence.facts` and `TenantIntelligence.classification` in place.

### `parsing.py`

| Function | Input | Output |
|----------|-------|--------|
| `parse_tenant_ai_response(raw_text)` | Claude response string | Parsed dict or raises `ValueError` if not valid JSON |
| `parse_maintenance_draft_response(raw_text)` | Claude response for maintenance draft | Dict with `trade`, `urgency`, `draft_message` keys |

Both functions expect Claude to return JSON. If the response is not parseable JSON,
they raise `ValueError`. Tests must cover valid JSON, invalid JSON, and partial JSON cases.

### `skills_registry.py`

| Function | Returns |
|----------|---------|
| `get_claude_skills()` | List of Anthropic tool dicts for general Claude interactions |
| `get_maintenance_skills()` | List of tools specific to maintenance triage |
| `get_full_registry()` | Merged list of all available tools |

Tool dicts follow the Anthropic tools API format:
```python
{
    "name": "create_maintenance_request",
    "description": "...",
    "input_schema": {"type": "object", "properties": {...}, "required": [...]}
}
```

Tests should verify: all required keys present, `name` values match what views call,
no duplicate tool names in the registry.

### `tenant_context.py` — `build_tenant_context(tenant_user, session)`

Assembles the context window sent to Claude for a tenant chat turn:
- Recent messages from the session
- Tenant intelligence facts
- Active lease details
- Maintenance history summary
- Property info (from `UnitInfo`)

Returns a list of message dicts ready for the Anthropic messages API.

---

## Management Commands

| Command | Purpose |
|---------|---------|
| `train_from_chats` | Export chat sessions as training examples for fine-tuning |
| `tenant_ai_training` | Generate synthetic training data from tenant intelligence records |

---

## Claude Model

**Model used:** `claude-sonnet-4-6`

Always mock Anthropic API calls in tests. Never make live Claude calls in the test suite.

```python
@patch("apps.ai.parsing.anthropic.Anthropic")
def test_parse_returns_trade_key(self, MockAnthropic):
    mock_client = MagicMock()
    MockAnthropic.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"trade": "plumbing", "urgency": "high"}')]
    )
    from apps.ai.parsing import parse_maintenance_draft_response
    result = parse_maintenance_draft_response("burst pipe in kitchen")
    assert result["trade"] == "plumbing"
    assert result["urgency"] == "high"
```

---

## Key Invariants

- Claude responses used by `parse_*` functions must be valid JSON strings
- Skill `name` values in the registry must be unique and match exactly what views reference
- `TenantIntelligence` is OneToOne with `User` — at most one intelligence record per tenant
- `build_tenant_context` must never leak one tenant's data into another tenant's context
- Management commands must be idempotent (re-running does not duplicate records)

---

## Integration Dependencies

- **Anthropic Claude API** — all AI calls (mock in tests)
- `apps.tenant_portal` — `TenantChatSession` referenced by the portal
- `apps.leases` — lease details included in tenant context
- `apps.maintenance` — maintenance history included in tenant context

---

## Known Test Areas

- `parse_tenant_ai_response`: valid JSON dict → returns dict
- `parse_tenant_ai_response`: non-JSON string → raises ValueError
- `parse_tenant_ai_response`: JSON array (not dict) → handled gracefully
- `parse_maintenance_draft_response`: valid response → correct keys extracted
- `parse_maintenance_draft_response`: missing required key → raises ValueError or returns default
- `get_full_registry()`: no duplicate tool names; all required schema keys present
- `get_maintenance_skills()`: returns at least one tool with `name = "create_maintenance_request"`
- `update_tenant_intel`: mock Claude → `TenantIntelligence` record created/updated
- `build_tenant_context`: returns list of message dicts; no cross-tenant data leak

---

## Coverage Gaps

- `build_tenant_context` unit tests (verify correct data sources assembled)
- `update_tenant_intel` classification edge cases (no chat history, very long history)
- Training management command tests (verify output format)
- Skills registry completeness regression (add test to catch unregistered tools)

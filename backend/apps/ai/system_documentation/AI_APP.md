# AI App (`apps.ai`)

Centralised AI intelligence layer for Tremly Property Manager. Owns tenant chat storage, cross-chat intelligence profiles, response parsing, training fixtures, and the MCP server that exposes tenant context to external AI agents.

## Overview

The AI app is the backbone of tenant-facing AI features. It handles:

1. **Chat Storage** — Every tenant↔AI conversation is stored as a single database row with the full message thread in a JSONB column (`TenantChatSession`).
2. **Tenant Intelligence** — Accumulated behavioural profile per tenant, updated after every AI exchange (`TenantIntelligence`).
3. **Response Parsing** — Pure-function parsers that extract structured data from Claude's JSON responses (maintenance tickets, conversation titles, draft reports).
4. **Training & Validation** — A JSON fixture of test cases with embedded parse-regression checks, plus a management command to validate them.
5. **MCP Server** — A standalone FastMCP process (stdio) that exposes chat history and intelligence profiles to Cursor, external agents, and training pipelines.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Tenant Mobile App                        │
│                    (Flutter / React Native)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │  POST /api/v1/tenant-portal/conversations/{id}/messages/
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Django Backend                              │
│                                                                  │
│   ┌──────────────────────┐    ┌──────────────────────────────┐  │
│   │  tenant_portal/views │────│  ai/parsing.py               │  │
│   │  (API endpoints)     │    │  (parse Claude JSON)         │  │
│   └──────────┬───────────┘    └──────────────────────────────┘  │
│              │                                                    │
│              │  writes messages (JSONB)                           │
│              │  calls update_tenant_intel()                       │
│              ▼                                                    │
│   ┌──────────────────────┐    ┌──────────────────────────────┐  │
│   │  ai/models.py        │    │  ai/intel.py                 │  │
│   │  TenantChatSession   │────│  update_tenant_intel()       │  │
│   │  TenantIntelligence  │    │  (rule-based, no AI cost)    │  │
│   └──────────┬───────────┘    └──────────────────────────────┘  │
│              │                                                    │
│              │  RAG context for Claude                            │
│              │                                                    │
│   ┌──────────────────────┐    ┌──────────────────────────────┐  │
│   │  core/contract_rag   │    │  core/anthropic_web_fetch    │  │
│   │  (ChromaDB vectors)  │    │  (optional URL fetching)     │  │
│   └──────────────────────┘    └──────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │  same PostgreSQL
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              MCP Server (mcp_server/server.py)                   │
│              FastMCP · stdio transport · read-only               │
│                                                                  │
│   Tools: get_chat_session, list_tenant_chats,                   │
│          get_tenant_context, search_tenant_chats,               │
│          list_property_chats                                     │
│                                                                  │
│   Resources: tenant://chats/{user_id}                           │
│              tenant://chats/{user_id}/latest                    │
│              tenant://intel/{user_id}                            │
│              tenant://property/{property_id}/chats              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                   Cursor / External AI Agents
                   Training Pipelines
```

---

## Models

### `TenantChatSession`

One row per tenant↔AI conversation thread. The entire message history lives in a single JSONB column rather than a separate messages table — optimised for fast whole-thread reads and simple backups.

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `user` | FK → User | The tenant who owns this thread (CASCADE) |
| `title` | CharField(200) | Thread title for the chat list (default "AI Assistant") |
| `maintenance_report_suggested` | BooleanField | True once the AI identifies a maintenance issue |
| `messages` | JSONField | Ordered array of message objects (see Message Object below) |
| `maintenance_request` | FK → MaintenanceRequest | Set when a maintenance request is created from this chat (SET_NULL) |
| `agent_question` | FK → AgentQuestion | Optional link to a staff agent question (SET_NULL) |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |

**Ordering:** `-updated_at` (most recent thread first).

#### Message Object (JSON shape)

Each element in the `messages` array:

```json
{
  "id": 1,
  "role": "user" | "assistant",
  "content": "Message text",
  "created_at": "2026-03-25T14:30:00+02:00",
  "attachment_kind": "" | "image" | "video",
  "attachment_storage": "tenant_ai/2026/03/abc123.jpg"
}
```

| Key | Type | Notes |
|-----|------|-------|
| `id` | int | Auto-incrementing within the session (1, 2, 3…) |
| `role` | string | `"user"` for tenant messages, `"assistant"` for AI |
| `content` | string | Message text; for uploads without text, a placeholder like "(Photo attached)" |
| `created_at` | ISO 8601 | Timezone-aware timestamp |
| `attachment_kind` | string | Empty string if no attachment; `"image"` or `"video"` |
| `attachment_storage` | string | Optional; storage path under `default_storage` (e.g. `tenant_ai/2026/03/uuid.jpg`) |

#### FK Links

- **`maintenance_request`** — Populated automatically when the AI response contains a `maintenance_ticket` and the system creates a `MaintenanceRequest`. The session is linked so staff can trace the original conversation.
- **`agent_question`** — Reserved for staff workflows where a question is escalated from a chat thread. Not auto-populated in the tenant flow yet.

---

### `TenantIntelligence`

One-to-one profile per tenant, updated after every AI exchange. Provides cross-chat context without requiring the AI to re-read all prior sessions.

| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOneField → User | The tenant (CASCADE) |
| `property_ref` | FK → Property | Resolved from the tenant's active lease (SET_NULL) |
| `unit_ref` | FK → Unit | Resolved from the tenant's active lease (SET_NULL) |
| `facts` | JSONField | Flexible key-value store for extracted facts |
| `question_categories` | JSONField | Category → count map, e.g. `{"maintenance_ticket": 4, "general_enquiry": 12}` |
| `total_chats` | PositiveIntegerField | Number of chat sessions for this tenant |
| `total_messages` | PositiveIntegerField | Total messages across all sessions |
| `complaint_score` | FloatField | 0–1 ratio of maintenance/complaint interactions to total |
| `last_chat_at` | DateTimeField | Timestamp of most recent chat exchange |
| `created_at` | DateTimeField | Auto-set on creation |
| `updated_at` | DateTimeField | Auto-updated on save |

#### `facts` JSONB Examples

```json
{
  "contact_preference": "WhatsApp",
  "known_issues": ["recurring damp in bedroom", "noisy neighbours"],
  "notes": "Tenant prefers morning visits for maintenance"
}
```

The `facts` field is intentionally unstructured to accommodate any information revealed during chat without schema changes.

#### How Intelligence Is Updated

`apps.ai.intel.update_tenant_intel()` is called after every AI response in the tenant portal view. It is **rule-based** — no extra Claude call is made:

1. **Property/unit resolution** — On first call, looks up the tenant's active lease to find their property and unit.
2. **Count refresh** — Recalculates `total_chats` and `total_messages` from the database.
3. **Category increment** — Classifies the exchange as `"maintenance_ticket"` (if the AI returned a non-null ticket) or `"general_enquiry"`, and increments the counter.
4. **Complaint score** — Recomputes the ratio of maintenance interactions to total.
5. **Timestamp** — Updates `last_chat_at`.

---

## Response Parsing (`ai/parsing.py`)

Pure functions with no Django dependencies (except for import paths). These are thoroughly unit-tested and used by both the API views and the training validation system.

### `parse_tenant_ai_response(raw: str) → (reply, maintenance_ticket, json_ok, conversation_title)`

Parses the structured JSON that Claude returns during a normal tenant chat. The expected shape:

```json
{
  "reply": "Human-readable response to the tenant",
  "conversation_title": "Short thread title" | null,
  "maintenance_ticket": {
    "title": "Staff-facing title",
    "description": "Full detail for maintenance team",
    "priority": "low" | "medium" | "high" | "urgent"
  } | null
}
```

**Returns:**
- `reply` (str) — The text to show the tenant. Falls back to raw text if JSON parsing fails.
- `maintenance_ticket` (dict | None) — Parsed ticket object, or None.
- `json_ok` (bool) — Whether the raw response was valid JSON.
- `conversation_title` (str | None) — Suggested thread title, or None.

Handles edge cases: markdown code fences around JSON, non-dict `maintenance_ticket` values, missing `reply` field.

### `parse_maintenance_draft_response(raw: str) → dict | None`

Parses the second-step "maintenance draft" AI response that converts a full chat transcript into a structured form:

```json
{
  "title": "Short actionable title for staff",
  "description": "Full detail for maintenance staff",
  "priority": "low" | "medium" | "high" | "urgent",
  "category": "plumbing" | "electrical" | "roof" | "appliance" | "security" | "pest" | "garden" | "other"
}
```

Validates priority and category against allowed values, falling back to `"medium"` / `"other"` for unknowns.

### `strip_json_fence(raw: str) → str`

Strips markdown `` ```json ... ``` `` fences from Claude responses that sometimes include them despite the system prompt requesting raw JSON.

---

## Tenant Portal API Endpoints

All endpoints require JWT authentication. Base path: `/api/v1/tenant-portal/`

### `GET /conversations/`
List all conversations for the authenticated tenant, ordered by most recent.

**Response:**
```json
[
  {
    "id": 1,
    "title": "Kitchen leak",
    "last_message": "I've flagged a leaking kitchen tap...",
    "updated_at": "2026-03-25T14:30:00+02:00"
  }
]
```

### `POST /conversations/`
Create a new conversation thread.

**Request body:** `{"title": "My Issue"}` (optional; defaults to "New conversation")

**Response:** `201` with the same shape as a list item.

### `GET /conversations/{id}/`
Full conversation detail including all messages.

**Response:**
```json
{
  "id": 1,
  "title": "Kitchen leak",
  "maintenance_report_suggested": true,
  "maintenance_request_id": 42,
  "agent_question_id": null,
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "My kitchen tap is leaking",
      "attachment_url": null,
      "attachment_kind": ""
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "I've noted the leak for the maintenance team.",
      "attachment_url": null,
      "attachment_kind": ""
    }
  ]
}
```

### `POST /conversations/{id}/messages/`
Send a tenant message, receive an AI response. Supports file uploads (multipart/form-data).

**Request:**
- `content` (string) — Message text
- `file` or `attachment` (file) — Optional image (JPEG, PNG, GIF, WebP) or video (MP4, MOV)

**Processing flow:**

1. Validate input (text and/or file required; file type/size checks)
2. Store upload to `default_storage` if present
3. Append user message to session's `messages` JSON
4. Query RAG (ChromaDB) for relevant contract/lease excerpts
5. Build Claude messages array from full conversation history (images sent as base64)
6. Call Anthropic Claude API with system prompt + RAG context + conversation history
7. Parse structured JSON response → extract reply, maintenance ticket, conversation title
8. If maintenance ticket detected → auto-create `MaintenanceRequest` and link to session
9. Append AI message to session's `messages` JSON
10. Update `TenantIntelligence` profile
11. Return response payload

**Response:**
```json
{
  "user_message": { "id": 1, "role": "user", "content": "...", "attachment_url": null, "attachment_kind": "" },
  "ai_message": { "id": 2, "role": "assistant", "content": "...", "attachment_url": null, "attachment_kind": "" },
  "conversation": { "id": 1, "title": "Kitchen leak" },
  "maintenance_request": { "id": 42, "title": "Kitchen tap leaking", "priority": "medium", "status": "open" } | null,
  "maintenance_report_suggested": true,
  "maintenance_request_id": 42,
  "agent_question_id": null
}
```

**Size limits (configurable via `.env`):**
- Images: 12 MB (`TENANT_AI_MAX_IMAGE_BYTES`)
- Videos: 45 MB (`TENANT_AI_MAX_VIDEO_BYTES`)

### `POST /conversations/{id}/maintenance-draft/`
Convert a conversation into a structured maintenance report form.

Only works if `maintenance_report_suggested` is True (i.e. the AI has already identified a maintenance issue in the chat).

**Response:**
```json
{
  "title": "Leaking kitchen tap",
  "description": "Tenant reports continuous drip from the kitchen mixer tap...",
  "priority": "medium",
  "category": "plumbing"
}
```

---

## Claude System Prompt

The tenant AI uses a detailed system prompt (`TENANT_SYSTEM_PROMPT` in `tenant_portal/views.py`) that instructs Claude to:

- Act as Tremly's residential tenant assistant for South African properties
- Use retrieved document excerpts (RAG) and cite sources
- Keep responses brief for simple FAQs (2–5 sentences, under ~120 words)
- Return structured JSON with `reply`, `conversation_title`, and `maintenance_ticket`
- Set `maintenance_ticket` to non-null only for real property issues (repairs, damage, leaks, break-ins, etc.)
- Use appropriate priority levels (urgent for emergencies, high for serious, medium default, low for cosmetic)
- Not provide legal advice; suggest Rental Housing Tribunal for disputes
- Only use `web_fetch` if the tenant explicitly provides a URL

**Emergency handling:** A heuristic fallback (`_heuristic_severe_ticket`) catches keywords like "break-in", "burglary", "gas smell", "ceiling collapsed" and creates an urgent ticket even if Claude's JSON parsing fails.

---

## RAG Integration (Contract Documents)

The tenant AI is augmented with a local ChromaDB vector store containing lease agreements, house rules, and property policies.

- **Ingestion:** `core/contract_rag.py` → `ingest_contract_documents()` walks `CONTRACT_DOCUMENTS_ROOT`, extracts text from PDF/DOCX/TXT/MD files, chunks it (1200 chars, 150 overlap), and upserts into ChromaDB.
- **Query:** `query_contracts(query, n_results=8)` retrieves the most relevant chunks for the tenant's message and prepends them to the Claude system prompt.
- **Settings:** `CONTRACT_DOCUMENTS_ROOT`, `RAG_CHROMA_PATH`, `RAG_PDF_MAX_PAGES`, `RAG_MAX_FILE_BYTES`, `RAG_QUERY_CHUNKS`

---

## MCP Server

A standalone FastMCP server (`backend/mcp_server/server.py`) that provides read-only access to tenant chat data and intelligence profiles. Designed for AI agent interoperability — Cursor, Claude Desktop, external training pipelines, and any MCP-compatible client can connect.

### Running the Server

```bash
cd backend
python mcp_server/server.py
```

The server bootstraps Django via `django.setup()` and uses the same database connection as the main backend.

### Cursor Integration

Configured in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tremly-tenant-context": {
      "command": "python",
      "args": ["backend/mcp_server/server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

### Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_chat_session` | `session_id: int` | Fetch a single session with full message thread |
| `list_tenant_chats` | `user_id: int`, `limit: int=20`, `include_messages: bool=False`, `has_maintenance_request: bool\|None` | List sessions for a tenant with optional filters |
| `get_tenant_context` | `user_id: int` | Full intelligence profile: user info, facts, categories, complaint score, recent chat summaries |
| `search_tenant_chats` | `user_id: int`, `query: str`, `limit: int=10` | Keyword search across all of a tenant's chat message content |
| `list_property_chats` | `property_id: int`, `limit: int=30` | All recent chats from tenants at a property (resolved via active leases) |

### Resources

| URI Template | Description |
|-------------|-------------|
| `tenant://chats/{user_id}` | All chat sessions for a tenant (full messages) |
| `tenant://chats/{user_id}/latest` | Most recent 5 chat sessions |
| `tenant://intel/{user_id}` | Intelligence profile for a tenant |
| `tenant://property/{property_id}/chats` | Recent chat summaries for all tenants at a property |

### Use Cases

- **Cursor AI context:** When working on tenant-related features, Cursor can pull a tenant's chat history and intelligence profile to understand their situation.
- **Training data extraction:** External pipelines can query all chats for a property to build training datasets.
- **Cross-agent context:** A maintenance dispatch agent can query `get_tenant_context` to understand the tenant's complaint history and preferred contact method before reaching out.
- **Quality analysis:** Query `search_tenant_chats` across tenants to find common issues or recurring complaints at a property.

---

## Training & Validation

### Fixture: `apps/ai/fixtures/tenant_ai_training_cases.json`

A versioned JSON file containing test cases for the tenant AI. Each case includes:

- `id` — Unique identifier (e.g. `"plumbing_kitchen_tap_drip"`)
- `summary` — Human-readable description
- `sample_transcript` — Example tenant↔AI exchange
- `tags` — Category tags (e.g. `["plumbing", "leak"]`)
- `expected_chat_json` — Schema expectations for the chat response
- `expected_draft_fields` — Expected fields for the maintenance draft
- `sample_chat_assistant_raw` — Raw Claude JSON to test parsing against
- `expect_chat_parse` — Parse regression assertions (json_ok, ticket priority, title contains, etc.)
- `sample_draft_model_raw` — Raw maintenance draft JSON to test parsing
- `expect_draft_parse` — Draft parse regression assertions

### Management Command

```bash
# List cases and basic schema validation
python manage.py tenant_ai_training

# Full parse regression check (no API calls)
python manage.py tenant_ai_training --parse-check

# Dump fixture JSON to stdout
python manage.py tenant_ai_training --json
```

### Validation Engine (`ai/training_validate.py`)

`validate_all_cases(data)` iterates every test case and runs `validate_case_parse(case)` which:

1. Parses `sample_chat_assistant_raw` through `parse_tenant_ai_response()`
2. Checks assertions in `expect_chat_parse`: `json_ok`, `maintenance_ticket_null`/`non_null`, `ticket_priority`, `ticket_title_contains`, `reply_nonempty`, `conversation_title_contains`/`non_null`
3. Parses `sample_draft_model_raw` through `parse_maintenance_draft_response()`
4. Checks assertions in `expect_draft_parse`: `non_null`/`null`, `category`, `priority`, `title_contains`, `description_contains`
5. Supports `one_of` matching for fields that accept multiple valid values

---

## Testing

### Test Suites

#### `apps.ai.tests.test_parsing` (SimpleTestCase — no database)

Unit tests for the pure parsing functions. No API calls, no database.

| Test | Description |
|------|-------------|
| `StripJsonFenceTests.test_plain_json_unchanged` | Plain JSON passes through unchanged |
| `StripJsonFenceTests.test_strips_fence` | Markdown code fences are stripped |
| `ParseTenantAiResponseTests.test_valid_json` | Correct parsing of valid JSON with reply, ticket, title |
| `ParseTenantAiResponseTests.test_markdown_fence` | JSON wrapped in markdown fences is parsed correctly |
| `ParseTenantAiResponseTests.test_invalid_json_returns_raw_reply_path` | Invalid JSON returns raw text as reply |
| `ParseTenantAiResponseTests.test_non_object_maintenance_ticket_dropped` | Non-dict maintenance_ticket is set to None |
| `ParseMaintenanceDraftTests.test_valid` | Correct parsing of a valid draft response |
| `ParseMaintenanceDraftTests.test_unknown_category_maps_to_other` | Unknown categories fall back to "other" |
| `ParseMaintenanceDraftTests.test_unknown_priority_maps_to_medium` | Unknown priorities fall back to "medium" |
| `ParseMaintenanceDraftTests.test_empty_title_returns_none` | Empty title returns None (invalid draft) |
| `TrainingFixtureTests.test_training_fixture_loads` | Fixture file loads and has correct structure |
| `TrainingFixtureTests.test_training_fixture_parse_regressions` | All embedded sample/expect pairs pass validation |

#### `apps.tenant_portal.tests.test_conversations` (TremlyAPITestCase — with database)

Integration tests for the conversation API. Claude calls are mocked.

| Test | Description |
|------|-------------|
| `ConversationListCreateTests.test_list_own_only` | Tenants only see their own conversations |
| `ConversationListCreateTests.test_create` | Creating a conversation returns 201 |
| `ConversationListCreateTests.test_create_custom_title` | Custom title is preserved |
| `ConversationListCreateTests.test_unauthenticated` | Unauthenticated requests get 401 |
| `ConversationDetailTests.test_get_detail` | Detail includes messages, maintenance_request_id, agent_question_id |
| `ConversationDetailTests.test_other_users_404` | Cannot access another tenant's conversation |
| `ConversationMessageTests.test_send_message_success` | Full message flow with mocked Claude |
| `ConversationMessageTests.test_send_message_empty` | Empty message returns 400 |
| `ConversationMessageTests.test_no_api_key` | Missing API key returns graceful fallback |
| `ConversationMessageTests.test_ai_error_returns_502` | Claude API errors return 502 |
| `ConversationMessageTests.test_maintenance_ticket_created` | Ticket response auto-creates MaintenanceRequest |
| `ConversationMessageTests.test_other_users_convo_404` | Cannot post to another tenant's conversation |
| `ConversationMessageTests.test_file_upload_unsupported_type` | Non-image/video uploads rejected with 400 |
| `MaintenanceDraftTests.test_draft_success` | Maintenance draft endpoint returns structured form |
| `MaintenanceDraftTests.test_no_maintenance_context` | Draft fails if maintenance_report_suggested is False |
| `MaintenanceDraftTests.test_ai_error` | Claude errors return 502 |

### Running Tests

```bash
# AI parsing + training fixture tests only (no database needed for SimpleTestCase)
python manage.py test apps.ai.tests

# Conversation API integration tests
python manage.py test apps.tenant_portal.tests

# Both together
python manage.py test apps.ai.tests apps.tenant_portal.tests

# Full test suite
python manage.py test
```

### Mocking Strategy

The conversation tests mock:
- `_get_anthropic_api_key` → returns `"test-key"` or `""` (no key scenario)
- `anthropic.Anthropic` → mock client whose `messages.create()` returns a mock response
- `extract_anthropic_assistant_text` → returns the raw JSON string directly
- `query_contracts` → returns a fixed string (skips ChromaDB)
- `build_web_fetch_tools` → returns empty list

This means tests never call the real Anthropic API or ChromaDB, and run fast (~3 seconds for 28 tests).

---

## File Structure

```
backend/
├── apps/
│   └── ai/
│       ├── __init__.py
│       ├── apps.py                          # AppConfig (label="ai")
│       ├── models.py                        # TenantChatSession, TenantIntelligence
│       ├── admin.py                         # Django admin for both models
│       ├── parsing.py                       # Pure JSON parsers (no Django deps)
│       ├── intel.py                         # update_tenant_intel() — rule-based updater
│       ├── training_validate.py             # Fixture validation engine
│       ├── management/
│       │   └── commands/
│       │       └── tenant_ai_training.py    # `manage.py tenant_ai_training`
│       ├── fixtures/
│       │   ├── tenant_ai_training_cases.json
│       │   └── generate_tenant_ai_training_cases.py
│       ├── tests/
│       │   └── test_parsing.py              # Unit tests for parsers + fixture
│       ├── migrations/
│       │   ├── 0001_initial.py              # TenantChatSession
│       │   ├── 0002_migrate_legacy_tenant_chats.py
│       │   └── 0003_tenantintelligence.py   # TenantIntelligence
│       └── system_documentation/
│           └── AI_APP.md                    # This file
├── mcp_server/
│   ├── __init__.py
│   └── server.py                            # FastMCP stdio server
├── core/
│   ├── contract_rag.py                      # ChromaDB vector RAG
│   └── anthropic_web_fetch.py               # Optional web_fetch tool
└── apps/
    └── tenant_portal/
        ├── views.py                         # API views (uses ai/parsing, ai/intel)
        ├── urls.py                          # URL routing
        └── tests/
            └── test_conversations.py        # Integration tests
```

---

## Configuration (`.env` / `settings`)

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | `""` | Claude API key (required for AI features) |
| `CONTRACT_DOCUMENTS_ROOT` | `backend/documents` | Root directory for lease/policy documents |
| `RAG_CHROMA_PATH` | `backend/rag_chroma` | ChromaDB persistent storage path |
| `RAG_QUERY_CHUNKS` | `8` | Number of RAG chunks to retrieve per query |
| `RAG_PDF_MAX_PAGES` | `120` | Max PDF pages to extract for RAG |
| `RAG_MAX_FILE_BYTES` | `40MB` | Max file size for RAG ingestion |
| `TENANT_AI_MAX_IMAGE_BYTES` | `12MB` | Max image upload size |
| `TENANT_AI_MAX_VIDEO_BYTES` | `45MB` | Max video upload size |
| `ANTHROPIC_WEB_FETCH_ENABLED` | `False` | Enable Anthropic's hosted web_fetch tool |

---

## Migrations

| Migration | Description |
|-----------|-------------|
| `ai.0001_initial` | Creates `TenantChatSession` (depends on `maintenance.0009`) |
| `ai.0002_migrate_legacy_tenant_chats` | Copies legacy `tenant_portal.TenantAiConversation` + `TenantAiMessage` rows into JSONB format; resets PostgreSQL sequence |
| `ai.0003_tenantintelligence` | Creates `TenantIntelligence` |
| `tenant_portal.0004_remove_legacy_ai_models` | Drops old `TenantAiConversation` and `TenantAiMessage` tables (depends on `ai.0002`) |

**Migration order is enforced:** `tenant_portal.0004` depends on `ai.0002`, so data is always copied before the old tables are dropped.

---

## Django Admin

Both models are registered in `apps/ai/admin.py` with rich admin interfaces:

**TenantChatSessionAdmin:**
- List: id, title, user, maintenance_request, agent_question, maintenance_report_suggested, updated_at
- Filters: maintenance_report_suggested, updated_at
- Search: title, user email
- Fieldsets: core fields, links, messages JSON, preview (formatted), timestamps

**TenantIntelligenceAdmin:**
- List: user, property, unit, total_chats, total_messages, complaint_score, last_chat_at
- Filters: property, last_chat_at
- Search: user email, name
- Fieldsets: core fields, stats, data (facts + categories), previews (formatted JSON), timestamps

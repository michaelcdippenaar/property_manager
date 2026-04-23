# Leases Module E2E Testing via MCP Server

## Context
Create an MCP test server that Claude Code can call to directly interact with the running Tremly backend API (localhost:8000) for end-to-end testing of the entire leases module. The app frontend runs at localhost:5173. This MCP server acts as an HTTP API client, simulating real frontend behavior (JWT auth, REST calls).

## MCP Server Structure

```
services/tremly-mcp/
  package.json          # type: "module", deps: @modelcontextprotocol/sdk, zod
  server.mjs            # Entry point - registers all tools, stdio transport
  lib/
    http-client.mjs     # fetch wrapper with JWT token caching + auto-refresh
    tools/
      auth.mjs          # auth_login, auth_whoami, auth_status
      leases.mjs        # lease_list, lease_get, lease_create, lease_update, lease_delete, lease_calendar
      templates.mjs     # template_list/get/create/update/preview + template_tiptap_roundtrip
      builder.mjs       # builder_session_create/message/finalize, builder_draft_list/create/update
      clauses.mjs       # clause_list/create/delete/use/generate/extract
      esigning.mjs      # esigning_list/create/get/signer_status/resend/public_link/webhook_info
      documents.mjs     # document_parse, lease_import
      health.mjs        # health_check - pings all endpoints, returns status table
```

## Key Design Decisions

1. **HTTP client**: Node.js built-in `fetch` (no axios). JWT tokens stored in module-level vars. Auto-refresh on 401.
2. **No TypeScript**: Plain `.mjs` files for zero-build simplicity. Zod for input validation.
3. **Response format**: Every tool returns `{ok: true/false, data/error, status}` JSON.
4. **TipTap roundtrip test**: Composite tool that creates a template with v2 JSON envelope, re-fetches, and verifies the envelope survived.

## Backend API Endpoints to Cover

### Auth (`/api/v1/auth/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/login/` | JWT login → `{access, refresh, user}` |
| GET | `/me/` | Current user info |
| POST | `/token/refresh/` | Refresh JWT token |

### Leases (`/api/v1/leases/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/` | List/create leases |
| GET/PATCH/DELETE | `/{id}/` | Lease detail CRUD |
| GET | `/calendar/` | Lease calendar data |

### Templates (`/api/v1/leases/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/templates/` | List/create templates |
| GET/PATCH/DELETE | `/templates/{id}/` | Template detail CRUD |
| GET | `/templates/{id}/preview/` | HTML preview |
| POST | `/templates/{id}/ai-chat/` | AI-assisted editing |
| GET | `/templates/{id}/export.pdf` | PDF export |

### Builder (`/api/v1/leases/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/builder/sessions/` | Create builder session |
| POST | `/builder/sessions/{id}/message/` | Send chat message |
| POST | `/builder/sessions/{id}/finalize/` | Finalize to lease |
| GET | `/builder/drafts/` | List drafts |
| POST | `/builder/drafts/new/` | Create draft |
| PATCH | `/builder/drafts/{id}/` | Update draft |

### Clauses (`/api/v1/leases/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/clauses/` | List/create clauses |
| POST | `/clauses/generate/` | AI-generate clause |
| POST | `/clauses/extract/` | Extract from HTML |
| DELETE | `/clauses/{id}/` | Delete clause |
| POST | `/clauses/{id}/use/` | Mark clause used |

### E-Signing (`/api/v1/esigning/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET/POST | `/submissions/` | List/create submissions |
| GET/PATCH | `/submissions/{id}/` | Submission detail |
| GET | `/submissions/{id}/download/` | Download signed PDF |
| POST | `/submissions/{id}/resend/` | Resend invite |
| GET | `/submissions/{id}/signer-status/` | Poll signer status |
| POST | `/submissions/{id}/public-link/` | Create public link |
| GET | `/public-sign/{uuid}/` | Public signing page |
| GET | `/webhook/info/` | Webhook config |
| POST | `/webhook/` | DocuSeal webhook |

### Documents (`/api/v1/leases/`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/parse-document/` | AI-parse uploaded PDF/DOCX |
| POST | `/import/` | Atomic lease import |

## Tool Definitions

### Auth Tools (Priority: CRITICAL)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `auth_login` | Authenticate with backend API | `{email: string, password: string}` |
| `auth_whoami` | Get current authenticated user | `{}` |
| `auth_status` | Check auth state + token validity | `{}` |

### Lease CRUD Tools (Priority: CRITICAL)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `lease_list` | List leases with optional status filter | `{status?: string, page?: number}` |
| `lease_get` | Get single lease by ID | `{id: number}` |
| `lease_create` | Create a new lease | `{unit_id, primary_tenant_id, start_date, end_date, monthly_rent, deposit, ...}` |
| `lease_update` | Update lease fields | `{id: number, ...partial fields}` |
| `lease_delete` | Delete a lease | `{id: number}` |
| `lease_calendar` | Get lease calendar data | `{}` |

### Template Tools (Priority: CRITICAL)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `template_list` | List all active templates | `{}` |
| `template_get` | Get template with full content | `{id: number}` |
| `template_create` | Create a new template | `{name, content_html?, ...}` |
| `template_update` | Patch a template | `{id, content_html?, header_html?, footer_html?, ...}` |
| `template_preview` | Get template preview data | `{id: number}` |
| `template_ai_chat` | Send message to template AI chat | `{id: number, message: string}` |
| `template_tiptap_roundtrip` | Composite: create template with v2 TipTap JSON envelope, refetch, verify integrity | `{name?: string}` |

### Builder Tools (Priority: HIGH)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `builder_session_create` | Start builder session | `{template_id?: number}` |
| `builder_session_message` | Send chat message to builder | `{session_id: number, message: string}` |
| `builder_session_finalize` | Finalize to lease | `{session_id: number}` |
| `builder_draft_list` | List drafts | `{}` |
| `builder_draft_create` | Create draft | `{...draft fields}` |
| `builder_draft_update` | Update draft | `{id: number, ...fields}` |

### Clause Tools (Priority: MEDIUM)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `clause_list` | List reusable clauses | `{}` |
| `clause_create` | Create a clause | `{title, category, html, tags?}` |
| `clause_delete` | Delete a clause | `{id: number}` |
| `clause_use` | Mark clause as used | `{id: number}` |
| `clause_generate` | AI-generate clause | `{prompt: string}` |
| `clause_extract` | Extract clauses from HTML | `{html: string}` |

### E-Signing Tools (Priority: HIGH)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `esigning_list` | List submissions | `{}` |
| `esigning_create` | Create submission | `{lease_id: number, signers: [...], signing_mode: string}` |
| `esigning_get` | Get submission detail | `{id: number}` |
| `esigning_signer_status` | Check signer status | `{id: number}` |
| `esigning_resend` | Resend invite | `{id: number}` |
| `esigning_public_link` | Create public link | `{id: number, signer_role: string}` |
| `esigning_webhook_info` | Get webhook config | `{}` |

### Document Tools (Priority: MEDIUM)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `document_parse` | Parse uploaded lease document | `{file_path: string}` |
| `lease_import` | Import parsed data | `{...parsed data}` |

### Health Check (Priority: HIGH)
| Tool Name | Description | Input |
|-----------|-------------|-------|
| `health_check` | Ping all endpoints, return status table | `{include_auth?: boolean}` |

## HTTP Client Design (`lib/http-client.mjs`)

```js
// Module-level token storage (session-scoped, no persistence)
let accessToken = null;
let refreshToken = null;
let currentUser = null;

const BASE_URL = process.env.TREMLY_API_URL || 'http://localhost:8000/api/v1/';

export async function login(email, password)     // POST /auth/login/ → cache tokens
export async function apiGet(path)               // GET with Authorization header
export async function apiPost(path, body)        // POST with Authorization header
export async function apiPatch(path, body)       // PATCH with Authorization header
export async function apiDelete(path)            // DELETE with Authorization header
export function isAuthenticated()                // boolean check
export function getCurrentUser()                 // return cached user

// Auto-refresh: on 401 response, try POST /auth/token/refresh/ with refresh token
// If refresh also fails, return auth error
```

## Implementation Phases

### Phase 1: Foundation (build first)
1. Create `package.json` with `"type": "module"`
2. Install: `npm install @modelcontextprotocol/sdk zod`
3. Create `lib/http-client.mjs`
4. Create `server.mjs` entry point
5. Create `lib/tools/auth.mjs`
6. Create `lib/tools/health.mjs`
7. Register in `.claude/settings.json` as `tremly-e2e`
8. Test: `auth_login` → `health_check`

### Phase 2: Core CRUD
9. Create `lib/tools/leases.mjs`
10. Create `lib/tools/templates.mjs` (including TipTap roundtrip)

### Phase 3: AI Flows
11. Create `lib/tools/builder.mjs`
12. Create `lib/tools/clauses.mjs`

### Phase 4: E-Signing & Documents
13. Create `lib/tools/esigning.mjs`
14. Create `lib/tools/documents.mjs`

## Registration in `.claude/settings.json`

```json
"tremly-e2e": {
  "command": "node",
  "args": ["services/tremly-mcp/server.mjs"],
  "cwd": "/Users/mcdippenaar/PycharmProjects/tremly_property_manager",
  "env": {
    "TREMLY_API_URL": "http://localhost:8000/api/v1/",
    "TREMLY_FRONTEND_URL": "http://localhost:5173"
  }
}
```

## Testing Sequence (after MCP server is built)
1. `auth_login` with test credentials
2. `health_check` to verify all endpoints respond
3. `template_list` → `template_create` → `template_tiptap_roundtrip`
4. `lease_list` → `lease_create` (needs existing property/unit/person)
5. `builder_session_create` → `builder_session_message` to test AI chat
6. `esigning_list` to verify e-signing state
7. `clause_list` → `clause_create` → `clause_delete`

## Potential Challenges
- **File uploads**: `document_parse` needs multipart form data — use `FormData` + `Blob` from Node 18+
- **Long-running AI calls**: Builder chat may take 10-30s — set appropriate fetch timeouts
- **DocuSeal dependency**: E-signing needs running DocuSeal container — health check should detect this
- **Test data**: Many tools need existing property/unit/person data — use existing test account
- **Pagination**: Lease list is paginated — tool should pass through pagination params

## Dependencies
- `@modelcontextprotocol/sdk` — MCP server framework
- `zod` — input schema validation
- Node.js 18+ built-in `fetch` — HTTP client (no axios needed)

## TipTap Roundtrip Test Detail

The `template_tiptap_roundtrip` tool is a composite test that verifies the v2 JSON envelope survives a save/load cycle:

1. POST new template with `content_html` = `JSON.stringify({v: 2, html: "<p>Test merge field: {{tenant_name}}</p>", tiptapJson: {type: "doc", content: [{type: "paragraph", content: [{type: "text", text: "Test merge field: "}, {type: "mergeField", attrs: {fieldName: "tenant_name"}}]}]}, fields: [{fieldName: "tenant_name", fieldType: "text"}]})`
2. GET the template back by ID
3. Parse `content_html` from response
4. Assert: `parsed.v === 2`
5. Assert: `parsed.html` contains the original HTML
6. Assert: `parsed.tiptapJson.content` is intact
7. Assert: `parsed.fields` array is intact
8. Clean up: DELETE the test template
9. Return structured pass/fail results

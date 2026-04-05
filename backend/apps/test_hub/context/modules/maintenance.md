# Module: maintenance

**App path:** `apps/maintenance/`
**Domain:** Maintenance requests, supplier directory, job dispatch and quoting, AI agent assistance, WebSocket updates.

---

## Models

| Model | Key Fields |
|-------|-----------|
| `Supplier` | `linked_user` (FK→User, nullable), `name`, `company_name`, `phone`, `email`, `website`, `address`, `city`, `province`, `latitude`, `longitude`, `service_radius_km`, `bee_level`, `cidb_grading`, `insurance_expiry`, `rating` (1.0–5.0), `ai_profile` (JSON), `is_active` |
| `SupplierTrade` | `supplier` (FK), `trade` (plumbing/electrical/carpentry/painting/roofing/hvac/locksmith/pest_control/landscaping/appliance/general/security/cleaning/other) |
| `SupplierDocument` | `supplier` (FK), `document_type` (bank_confirmation/bee_certificate/insurance/cidb/company_reg/tax_clearance/other), `file`, `description` |
| `SupplierProperty` | `supplier` (FK→Supplier), `property` (FK→Property), `is_preferred`, `notes` |
| `MaintenanceRequest` | `unit` (FK→Unit), `tenant` (FK→User), `supplier` (FK→Supplier, nullable), `title`, `description`, `priority` (low/medium/high/urgent), `status` (open/in_progress/resolved/closed), `image` |
| `JobDispatch` | `maintenance_request` (OneToOne→MaintenanceRequest), `status` (draft/sent/quoting/awarded/cancelled), `dispatched_by` (FK→User), `dispatched_at`, `notes` |
| `JobQuoteRequest` | `dispatch` (FK→JobDispatch), `supplier` (FK→Supplier), `status` (pending/viewed/quoted/declined/awarded/expired), `token` (UUID), `match_score`, `match_reasons` (JSON), `notified_at`, `viewed_at` |
| `JobQuote` | `quote_request` (OneToOne→JobQuoteRequest), `amount` (ZAR Decimal), `description`, `estimated_days`, `available_from` |
| `MaintenanceSkill` | Named skill/trade classification used by AI matching. Fields: `name`, `description`, `trade_category` |
| `AgentQuestion` | Pending question the AI agent needs the human agent to answer. Fields: `maintenance_request` (FK), `question_text`, `answer`, `answered_at`, `is_answered` |
| `MaintenanceActivity` | Activity log entry for a maintenance request. Fields: `maintenance_request` (FK), `actor` (FK→User), `activity_type`, `notes`, `created_at` |
| `AgentTokenLog` | Tracks Anthropic API token usage per AI agent request. Fields: `request` (FK), `input_tokens`, `output_tokens`, `model` |

---

## Supplier Matching Algorithm

**File:** `apps/maintenance/matching.py` — `rank_suppliers(maintenance_request)`

Scores suppliers 0–100 using weighted factors:

| Factor | Weight | Logic |
|--------|--------|-------|
| Proximity | 30% | Haversine distance; excluded if outside `service_radius_km` |
| Skills match | 25% | Trade alignment between `SupplierTrade` and request category |
| Price history | 15% | Average `JobQuote.amount` vs global average (lower = better) |
| Owner preference | 20% | `SupplierProperty.is_preferred` for the relevant property |
| Rating | 10% | `Supplier.rating` (1.0–5.0 normalised) |

Returns: top N suppliers sorted by score, each with `match_score` and `match_reasons` JSON.

When testing matching, mock `Supplier.latitude`/`longitude` to control proximity scores.

---

## AI Agent Assist

**File:** `apps/maintenance/agent_assist_views.py`

Claude assists agents by:
- Diagnosing maintenance issues from description + images
- Drafting supplier communication
- Answering questions about the property playbook
- Flagging urgent/safety issues

`AgentQuestion` records are created when Claude needs human input.
Answered questions are ingested into a RAG vector store (via signals).

---

## Job Flow

```
1. MaintenanceRequest created (tenant or agent)
2. Agent creates JobDispatch (status: draft)
   → rank_suppliers() returns scored list
3. Agent sends dispatch (status: sent)
   → JobQuoteRequest created per selected supplier
   → Each supplier notified via token link
4. Supplier views job (QuoteRequest status: viewed)
5. Supplier submits JobQuote (QuoteRequest status: quoted)
   OR declines (QuoteRequest status: declined)
6. Agent awards job to one supplier (QuoteRequest status: awarded, others: expired)
   → MaintenanceRequest.supplier set
   → MaintenanceRequest.status → in_progress
7. Work completed → status → resolved → closed
```

---

## Token-Based Quote Pages

Suppliers access job details via a tokenised URL (no auth required):
- `GET  /api/v1/maintenance/quotes/{token}/` — view job
- `POST /api/v1/maintenance/quotes/{token}/` — submit quote
- `POST /api/v1/maintenance/quotes/{token}/decline/` — decline

`token` is a UUID on `JobQuoteRequest`. These endpoints are unauthenticated.

---

## Signals

`apps/maintenance/signals.py`:
- Broadcasts `MaintenanceRequest` status changes via Django Channels WebSocket
- Ingests answered `AgentQuestion` records into the RAG vector store for future AI context

---

## Management Commands

| Command | Purpose |
|---------|---------|
| `seed_skills` | Populate `MaintenanceSkill` table with standard trade skills |
| `vectorize_issues` | Embed maintenance request descriptions for RAG search |
| `ingest_contract_documents` | Embed contract/playbook documents into vector store |
| `backfill_chat_history` | Backfill historical chat messages into training data |

---

## Key Invariants

- A `JobDispatch` is OneToOne with `MaintenanceRequest` — only one active dispatch
- `JobQuote` is OneToOne with `JobQuoteRequest` — one quote per request
- Dispatch requires `status=draft` before it can be sent
- Awarding a job sets all other `JobQuoteRequest` statuses to `expired`
- `quote.amount` must be positive
- A supplier can only be dispatched once per maintenance request (prevent duplicates in `JobQuoteRequest`)
- Token-based endpoints must not require authentication headers

---

## Integration Dependencies

- **Anthropic Claude API** — AI agent assist views, maintenance triage
- **Django Channels (WebSocket)** — real-time broadcast of status changes
- **RAG vector store** — ChromaDB or similar, receives answered questions and contract docs
- **Google Maps / geocoding** — supplier `latitude`/`longitude` for proximity matching

---

## Known Test Areas

- MaintenanceRequest CRUD: create (tenant/agent), update status, list by role
- Tenant can only see their own requests; agent sees all in their properties
- Supplier matching: verify rank_suppliers returns correct order based on mocked factors
- Job dispatch: create dispatch → send → quote submitted → award
- Token endpoint: submit quote without auth → 200; bad token → 404
- Token endpoint: submit quote after dispatch expired → 400
- Supplier portal: supplier user sees only their assigned jobs
- AgentQuestion: created by AI, answered by agent, marked is_answered

---

## Coverage Gaps

- WebSocket consumer tests (Channels `WebsocketCommunicator`)
- AI agent response validation (mock Claude → verify AgentQuestion created)
- Signal handler unit tests (status broadcast, RAG ingestion)
- `rank_suppliers` unit tests with controlled geographic data
- Excel import: `POST /maintenance/suppliers/import_excel/`
- `AgentTokenLog` usage tracking accuracy

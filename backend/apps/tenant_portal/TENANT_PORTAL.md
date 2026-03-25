# Tenant Portal App

AI-powered tenant assistant with conversational chat, maintenance issue detection, and RAG-enhanced document queries.

## Overview

The tenant portal provides an AI chatbot for residential tenants. Tenants can ask questions about their lease, property rules, or report maintenance issues. The AI uses RAG (Retrieval-Augmented Generation) over the landlord's document library and automatically creates maintenance requests when issues are detected. It also supports photo and video attachments.

---

## Model: `TenantChatSession`

Located in `apps/ai/models.py`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `user` | ForeignKey → User | Tenant who owns the conversation |
| `title` | CharField(200) | Conversation title (default: "AI Assistant") |
| `maintenance_report_suggested` | BooleanField | True once AI identifies a maintenance issue |
| `messages` | JSONField | Array of message objects (see below) |
| `maintenance_request` | ForeignKey → MaintenanceRequest | Linked MR (nullable) |
| `agent_question` | ForeignKey → AgentQuestion | Linked question (nullable) |
| `created_at` | DateTimeField | Auto-set |
| `updated_at` | DateTimeField | Auto-updated |

### Message Object Shape (in `messages` JSONField)

```json
{
  "id": 1,
  "role": "user",
  "content": "My tap is leaking",
  "created_at": "2026-03-25T12:00:00Z",
  "attachment_kind": "image",
  "attachment_storage": "tenant_ai/2026/03/abc123.jpg"
}
```

---

## API Endpoints

All endpoints prefixed with `/api/v1/tenant-portal/`.

---

### 1. List / Create Conversations

```
GET  /api/v1/tenant-portal/conversations/
POST /api/v1/tenant-portal/conversations/
```

**Auth:** Required

**GET Response:** `200 OK`

```json
[
  {
    "id": 1,
    "title": "Kitchen leak",
    "last_message": "I can help with that...",
    "updated_at": "2026-03-25T12:00:00Z"
  }
]
```

Users see only their own conversations, ordered by most recently updated.

**POST Request:**

```json
{
  "title": "My question"
}
```

Title defaults to "New conversation" if omitted.

**POST Response:** `201 Created`

```json
{
  "id": 2,
  "title": "My question",
  "last_message": "",
  "updated_at": "2026-03-25T12:00:00Z"
}
```

---

### 2. Conversation Detail

```
GET /api/v1/tenant-portal/conversations/{id}/
```

**Auth:** Required

**Response:** `200 OK`

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
      "content": "My tap is leaking",
      "attachment_url": null,
      "attachment_kind": ""
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "I can help with that...",
      "attachment_url": null,
      "attachment_kind": ""
    }
  ]
}
```

**Errors:** `404` if conversation belongs to a different user.

---

### 3. Send Message

```
POST /api/v1/tenant-portal/conversations/{id}/messages/
```

**Auth:** Required
**Parsers:** JSON, multipart/form-data (for file uploads)

**Request (JSON):**

```json
{
  "content": "My kitchen tap is leaking"
}
```

**Request (multipart with file):**

```
POST /api/v1/tenant-portal/conversations/{id}/messages/
Content-Type: multipart/form-data

content: "The bathroom is flooded, see photo"
file: [image or video file]
```

#### Supported File Types

| Type | Extensions | Max Size |
|------|-----------|----------|
| Image | JPEG, PNG, GIF, WebP, HEIC, HEIF | 12 MB |
| Video | MP4, MOV, M4V, WebM, 3GP | 45 MB |

#### Response: `200 OK`

```json
{
  "user_message": {
    "id": 1,
    "role": "user",
    "content": "My kitchen tap is leaking",
    "attachment_url": null,
    "attachment_kind": ""
  },
  "ai_message": {
    "id": 2,
    "role": "assistant",
    "content": "I understand the issue...\n\nWe've logged this for the property team (maintenance request #42).",
    "attachment_url": null,
    "attachment_kind": ""
  },
  "conversation": {
    "id": 1,
    "title": "Kitchen tap leaking"
  },
  "maintenance_request": {
    "id": 42,
    "title": "Kitchen tap leaking",
    "priority": "medium",
    "status": "open"
  },
  "maintenance_report_suggested": true,
  "maintenance_request_id": 42,
  "agent_question_id": null
}
```

`maintenance_request` is `null` if no maintenance issue was detected.

#### Error Responses

| Status | Reason |
|--------|--------|
| `400` | Empty content and no file |
| `400` | Unsupported file type |
| `400` | File too large |
| `404` | Conversation belongs to different user |
| `502` | AI API error |

---

### 4. Maintenance Draft

```
POST /api/v1/tenant-portal/conversations/{id}/maintenance-draft/
```

**Auth:** Required

Converts the conversation transcript into a structured maintenance report form using AI.

**Precondition:** `maintenance_report_suggested` must be `true` on the conversation.

**Request:** Empty POST body.

**Response:** `200 OK`

```json
{
  "title": "Kitchen tap leaking constantly",
  "description": "The kitchen sink tap has been dripping for a week. Water pooling at the base.",
  "priority": "medium",
  "category": "plumbing"
}
```

#### Error Responses

| Status | Reason |
|--------|--------|
| `400` | No maintenance context yet |
| `400` | No messages to summarize |
| `502` | AI error |
| `503` | AI unavailable (no API key) |

---

## AI Processing Flow

### Message Processing

1. **User sends message** → Stored in conversation's `messages` array
2. **RAG query** — User's message searched against landlord document library (ChromaDB)
   - Retrieves up to 8 chunks (configurable: `RAG_QUERY_CHUNKS`)
3. **Claude API call** — System prompt + RAG context + full conversation history
   - Model: `claude-sonnet-4-6`
   - Images sent as base64 inline
   - Videos noted as inaccessible to AI
4. **Parse AI response** — Expects JSON with `reply`, `conversation_title`, `maintenance_ticket`
5. **Maintenance detection** — If `maintenance_ticket` present and valid:
   - Creates `MaintenanceRequest` linked to tenant's active lease unit
   - Sets `maintenance_report_suggested = true`
   - Links MR to conversation via `maintenance_request_id`
6. **Heuristic fallback** — If JSON parsing fails but message contains emergency keywords (break-in, fire, flooding, etc.), creates an urgent maintenance request automatically
7. **Title update** — AI may suggest a conversation title (replaces generic "AI Assistant" / "New conversation")

### Emergency Keywords (Heuristic Detection)

```
break-in, break in, burglary, burglar, robbed, broken into,
forced entry, someone broke, stolen from, theft from, vandalis,
assault, attacked, fire in my, the flat flooded, burst pipe,
gas smell, ceiling collapsed
```

### AI Response Schema

The AI is instructed to return:

```json
{
  "reply": "Message to the tenant",
  "conversation_title": null | "Short thread name",
  "maintenance_ticket": null | {
    "title": "Short title for staff",
    "description": "What happened and what's needed",
    "priority": "low | medium | high | urgent"
  }
}
```

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `RAG_QUERY_CHUNKS` | 8 | Number of RAG chunks per query |
| `TENANT_AI_MAX_IMAGE_BYTES` | 12 MB | Max image upload size |
| `TENANT_AI_MAX_VIDEO_BYTES` | 45 MB | Max video upload size |
| `ANTHROPIC_WEB_FETCH_ENABLED` | — | Enable web fetch tool |

## Dependencies

- **Anthropic Claude** — AI responses and maintenance draft generation
- **ChromaDB** — RAG vector store for landlord documents
- **Django default_storage** — File uploads (local or S3)

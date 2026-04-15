# Volt Owner MCP

MCP server that lets Claude Desktop / Claude Code / Claude CoWork / claude.ai
custom connectors read and write your own Volt vault.

Two transports are supported, same tool set on both:

| Transport | Entry point | Auth | Client |
|---|---|---|---|
| **stdio** | `python -m apps.the_volt.mcp.server` | `VOLT_OWNER_API_KEY` env var | Claude Desktop / Code local config |
| **HTTP (streamable)** | `python manage.py volt_mcp_http` | `Authorization: Bearer <key>` header | claude.ai custom connector, curl, any HTTP MCP client |

## What it exposes

### Read tools
- `ensure_vault()` — confirm vault exists, return `{vault_id, user_email}`
- `list_entities(entity_type?, include_inactive?)`
- `find_entity(query, entity_type?)` — name substring search
- `get_entity(entity_id)` — full payload including in/out relationships
- `list_documents(entity_id?, document_type?)`
- `list_document_types(entity_type?)` — from `DocumentTypeCatalogue`

### Write tools
- `upsert_owner(name, id_number, date_of_birth, email, phone, address, tax_number, extra_data)`
- `upsert_property(name, address, registration_number, acquisition_date, acquisition_value, current_value, description, extra_data)`
- `upsert_tenant(name, id_number, email, phone, leases_property_id, extra_data)`
- `link_entities(from_entity_id, to_entity_id, relationship_type, metadata)`
- `attach_document(entity_id, document_type, label, file_base64, original_filename, mime_type, extracted_data)`

Every mutation is encrypted at rest (Fernet, per-owner key) and written to
`VaultWriteAudit` for a complete POPIA §17 processing log.

## 1. Generate an API key

```bash
cd backend
./.venv/bin/python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from apps.the_volt.owners.models import VaultOwner, VaultOwnerAPIKey

user = get_user_model().objects.get(email="you@example.com")
vault = VaultOwner.get_or_create_for_user(user)
key, raw = VaultOwnerAPIKey.create_for_owner(vault, label="Claude Desktop — MacBook")
print(raw)   # SAVE THIS — shown once
```

Or via Django admin: `/admin/the_volt/vaultownerapikey/` → *Add* → select your
`VaultOwner` → save → the raw key is shown in the success flash message.

## 2. Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "volt": {
      "command": "/absolute/path/to/tremly_property_manager/backend/.venv/bin/python",
      "args": ["-m", "apps.the_volt.mcp.server"],
      "cwd": "/absolute/path/to/tremly_property_manager/backend",
      "env": {
        "VOLT_OWNER_API_KEY": "volt_owner_REPLACE_ME",
        "DJANGO_SETTINGS_MODULE": "config.settings.local"
      }
    }
  }
}
```

Restart Claude Desktop. You should see a "volt" MCP badge in a new chat.

## 3. Register with Claude Code

```bash
claude mcp add volt \
  --scope user \
  --env VOLT_OWNER_API_KEY=volt_owner_REPLACE_ME \
  --env DJANGO_SETTINGS_MODULE=config.settings.local \
  -- /absolute/path/to/backend/.venv/bin/python -m apps.the_volt.mcp.server
```

## 4. Add as a claude.ai custom connector (HTTP)

Requires a Claude Pro / Max / Team / Enterprise account. Works from the web
and mobile apps — no local config.

### 4a. Dev (your PC) — tunnel with cloudflared

```bash
# terminal 1 — run the MCP HTTP server
cd backend
./.venv/bin/python manage.py volt_mcp_http --host 127.0.0.1 --port 8765
# -> http://127.0.0.1:8765/mcp/

# terminal 2 — expose it publicly
brew install cloudflare/cloudflare/cloudflared   # once
cloudflared tunnel --url http://127.0.0.1:8765
# -> https://some-random-words.trycloudflare.com
```

Copy the `trycloudflare.com` URL. Append `/mcp/` to get the connector URL.

Then in claude.ai:
1. Settings → Connectors → **Add custom connector**
2. **URL:** `https://some-random-words.trycloudflare.com/mcp/`
3. **Authentication:** Bearer token
4. **Token:** `volt_owner_REPLACE_ME`
5. Save → **Connect**

claude.ai will hit `/mcp/` with `Authorization: Bearer volt_owner_…` on every tool call.

### 4b. Staging — reverse-proxy at `backend.klikk.co.za/mcp/`

Run the HTTP server as a systemd unit / supervisord / Docker service on the
staging box, bound to `127.0.0.1:8765`. Then have your reverse proxy forward
`/mcp/` to it. Example nginx:

```nginx
location /mcp/ {
    proxy_pass http://127.0.0.1:8765/mcp/;
    proxy_http_version 1.1;
    proxy_set_header Host               $host;
    proxy_set_header X-Real-IP          $remote_addr;
    proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto  $scheme;
    proxy_set_header Authorization      $http_authorization;

    # Streamable HTTP = SSE-style long-poll. Disable buffering + long timeouts.
    proxy_buffering    off;
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;
}
```

Connector URL becomes `https://backend.klikk.co.za/mcp/` — no tunnel needed.

> **TLS required.** claude.ai refuses non-HTTPS connector URLs. In dev the
> `trycloudflare.com` URL is HTTPS-terminated for you. In staging the nginx
> TLS cert handles it.

## 5. Run standalone (debugging)

**Stdio mode:**
```bash
cd backend
VOLT_OWNER_API_KEY=volt_owner_… \
DJANGO_SETTINGS_MODULE=config.settings.local \
./.venv/bin/python -m apps.the_volt.mcp.server
```

**HTTP mode + curl probe:**
```bash
cd backend
./.venv/bin/python manage.py volt_mcp_http --port 8765

# In another shell — list tools:
curl -sN -X POST http://127.0.0.1:8765/mcp/ \
  -H 'Authorization: Bearer volt_owner_…' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## 6. First real session

In Claude Desktop, once `volt` is connected:

> Claude, use `ensure_vault` to confirm my vault is ready, then use
> `upsert_owner` to set me as the owner: my name is John Smith, SA ID
> 8001015009088, email john@example.com.
>
> Then use `upsert_property` to register my flat at 12 Dorp Street,
> Stellenbosch, title deed T12345/2020, acquired 2020-06-15 for R2,500,000.
>
> Finally, use `upsert_tenant` to add Jane Doe as a tenant, SA ID
> 9203125008089, leasing from that property.

You should see three `VaultEntity` rows and one `EntityRelationship`
in `/admin/the_volt/`, and four `VaultWriteAudit` rows.

## Security notes

- Raw API keys are shown **once**. Only the SHA-256 hash is persisted.
- Keys are scoped to **one** `VaultOwner` — one key can never read a different
  owner's vault. Compromised key = revoke from admin, all read + write
  paths stop immediately.
- File uploads hash the plaintext (`sha256_hash`), encrypt the bytes with
  Fernet before writing. The MCP process never keeps plaintext on disk.
- No consent flow is triggered for owner-MCP reads — the owner is reading
  their own data. External subscriber reads go through the gateway and
  produce `DataCheckout` records.
- Every mutation writes `VaultWriteAudit`. If the audit write fails, the
  mutation itself still succeeds (audit must not block writes) but the
  failure is logged.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `McpAuthError: VOLT_OWNER_API_KEY not set` | Env var missing in client config | Add to `env` in Claude Desktop config and restart |
| `Invalid or revoked Volt owner API key` | Wrong / revoked key | Generate a new key and update client config |
| `ModuleNotFoundError: apps.the_volt.mcp` | `cwd` wrong in client config | Point `cwd` to the `backend/` directory |
| Tool call hangs | Django settings wrong / DB not reachable | Check `DJANGO_SETTINGS_MODULE` matches your local env |

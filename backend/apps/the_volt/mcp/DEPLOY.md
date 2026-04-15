# Volt MCP — Staging Deployment Guide

> **For AI agents and humans deploying the Volt MCP server to `backend.klikk.co.za`.**
> Run through this top to bottom. Each section has a verification step — don't
> skip them.

---

## Context

The Volt MCP server is a FastMCP 3.x HTTP process (`volt_mcp_http`) that runs
alongside the Django backend. It exposes 11 owner tools over
`https://backend.klikk.co.za/mcp/` and is used by Claude CoWork / claude.ai
custom connectors to read and write the owner's data vault.

- **Django app:** `apps/the_volt/`
- **MCP server:** `apps/the_volt/mcp/http_server.py`
- **Management command:** `python manage.py volt_mcp_http`
- **Auth:** `Authorization: Bearer volt_owner_…` header on every request
- **Audit:** every mutation logged to `VaultWriteAudit`

---

## Prerequisites

- SSH access to the staging box running `backend.klikk.co.za`
- nginx already serving the Django backend on port 8000
- Python venv at `/opt/klikk/backend/.venv` (adjust path if different)
- Existing `.env` / environment with `DJANGO_SETTINGS_MODULE` set

---

## Step 1 — Pull latest code

```bash
cd /opt/klikk   # or wherever the repo lives on staging
git pull origin main
```

Verify the vault MCP files are present:
```bash
ls backend/apps/the_volt/mcp/
# Expected: README.md  DEPLOY.md  __init__.py  auth.py  audit.py
#           http_server.py  server.py  tools/
```

---

## Step 2 — Install dependencies

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

Verify fastmcp is installed:
```bash
python -c "import fastmcp; print(fastmcp.__version__)"
# Expected: 3.1.1 or higher
```

---

## Step 3 — Run the migration

```bash
python manage.py migrate the_volt
```

Expected output includes:
```
Applying the_volt.0004_phase_2_3_mcp_support... OK
```

If 0004 is already applied (re-deploy), this is a no-op — safe to run again.

Verify:
```bash
python manage.py showmigrations the_volt
# All four migrations should show [X]
```

---

## Step 4 — Generate a staging API key

Run the Django shell:
```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from apps.the_volt.owners.models import VaultOwner, VaultOwnerAPIKey

# Use the primary superuser / platform owner account
user = get_user_model().objects.filter(is_superuser=True).first()
print("Generating key for:", user.email)

vault = VaultOwner.get_or_create_for_user(user)
key, raw = VaultOwnerAPIKey.create_for_owner(vault, label="claude.ai connector — staging")
print("\nSAVE THIS KEY — shown once only:")
print(raw)
```

**Save the printed key.** It is shown once. Only the SHA-256 hash is stored in
the database. If lost, generate a new one and revoke the old one via
`/admin/the_volt/vaultownerapikey/`.

---

## Step 5 — Start the MCP server as a persistent service

### Option A — systemd (recommended)

Create `/etc/systemd/system/volt-mcp.service`:

```ini
[Unit]
Description=Volt Owner MCP HTTP Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=klikk
WorkingDirectory=/opt/klikk/backend
EnvironmentFile=/opt/klikk/.env
ExecStart=/opt/klikk/backend/.venv/bin/python manage.py volt_mcp_http \
    --host 127.0.0.1 \
    --port 8765
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable volt-mcp
sudo systemctl start volt-mcp
sudo systemctl status volt-mcp
```

Verify it's running:
```bash
curl -s http://127.0.0.1:8765/mcp/ \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}' \
  | head -c 200
# Expected: event: message  data: {"jsonrpc":"2.0","id":1,"result":{"serverInfo":{"name":"volt-owner"...
```

### Option B — supervisor

Add to `/etc/supervisor/conf.d/volt-mcp.conf`:
```ini
[program:volt-mcp]
command=/opt/klikk/backend/.venv/bin/python manage.py volt_mcp_http --host 127.0.0.1 --port 8765
directory=/opt/klikk/backend
user=klikk
autostart=true
autorestart=true
stderr_logfile=/var/log/klikk/volt-mcp.err.log
stdout_logfile=/var/log/klikk/volt-mcp.out.log
environment=DJANGO_SETTINGS_MODULE="config.settings.staging"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status volt-mcp
```

---

## Step 6 — Add nginx location block

Edit your nginx config for `backend.klikk.co.za`
(usually `/etc/nginx/sites-available/klikk-backend` or similar):

Add inside the `server { ... }` block, **before** the main `location /` block:

```nginx
# Volt Owner MCP — streamable HTTP endpoint
location /mcp/ {
    proxy_pass         http://127.0.0.1:8765/mcp/;
    proxy_http_version 1.1;

    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;

    # Forward the Authorization header — required for Volt bearer token auth
    proxy_set_header   Authorization     $http_authorization;

    # Streamable HTTP uses long-lived connections — disable buffering
    proxy_buffering    off;
    proxy_read_timeout 1h;
    proxy_send_timeout 1h;
}
```

Test and reload nginx:
```bash
sudo nginx -t          # must say: syntax is ok / test is successful
sudo nginx -s reload
```

---

## Step 7 — End-to-end smoke test through nginx

```bash
KEY="volt_owner_REPLACE_WITH_YOUR_STAGING_KEY"

# Initialize
curl -sN -X POST https://backend.klikk.co.za/mcp/ \
  -H "Authorization: Bearer $KEY" \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}'

echo ""

# List tools (stateless — no session ID needed)
curl -sN -X POST https://backend.klikk.co.za/mcp/ \
  -H "Authorization: Bearer $KEY" \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Expected: `tools/list` returns 11 tools including `ensure_vault`, `upsert_owner`, etc.

---

## Step 8 — Connect claude.ai

1. claude.ai → **Settings** → **Connectors** → **Add custom connector**
2. **URL:** `https://backend.klikk.co.za/mcp/`
3. **Authentication:** Bearer token / API Key
4. **Token:** `volt_owner_…` (from Step 4)
5. Save → **Connect**

This URL is permanent. The connector never needs to be recreated.

---

## Monitoring & logs

```bash
# systemd logs (live)
sudo journalctl -u volt-mcp -f

# supervisor logs
tail -f /var/log/klikk/volt-mcp.out.log

# Django admin — audit every mutation
# https://backend.klikk.co.za/admin/the_volt/vaultwriteaudit/

# Django admin — manage API keys
# https://backend.klikk.co.za/admin/the_volt/vaultownerapikey/
```

---

## Rotating an API key

```bash
python manage.py shell
```

```python
from apps.the_volt.owners.models import VaultOwner, VaultOwnerAPIKey
from django.contrib.auth import get_user_model

user = get_user_model().objects.filter(is_superuser=True).first()
vault = VaultOwner.get_or_create_for_user(user)

# Create new key
key, raw = VaultOwnerAPIKey.create_for_owner(vault, label="claude.ai connector — staging (rotated)")
print("New key:", raw)

# Revoke old key (find it by prefix in admin, or:)
# VaultOwnerAPIKey.objects.filter(label__contains="old label").first().revoke()
```

Update the token in the claude.ai connector settings. Old key stops working immediately.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502 Bad Gateway` from nginx | `volt-mcp` process not running | `sudo systemctl restart volt-mcp` |
| `Missing Authorization header` | nginx not forwarding `Authorization` | Check `proxy_set_header Authorization $http_authorization;` is in nginx config |
| `Invalid or revoked Volt owner API key` | Wrong key or revoked | Rotate key (see above) |
| `No tools available` in claude.ai | Session ID issue | Server is running `stateless_http=True` — if problem persists, restart the service |
| Tools visible but calls fail | DB connection issue | Check `DJANGO_SETTINGS_MODULE` in the service env matches the staging settings file |
| `Address already in use` on port 8765 | Previous process still running | `lsof -ti:8765 \| xargs kill -9` then restart service |

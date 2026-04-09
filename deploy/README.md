## Deploy admin + website (Docker)

Targets:
- Admin SPA: `propertymanager.klikk.co.za` -> `admin_web`
- Marketing site: `www.klikk.co.za` -> `website_web`
- Edge TLS + routing: `caddy`

### 1) DNS + network prerequisites

To serve these publicly with HTTPS:
- Point DNS A/AAAA records for both hostnames to your public IP.
- Forward router ports `80` and `443` to the Docker host (`192.168.1.245`).

If you do **not** want Google to detect anything, the safest approach is:
- **Do not** expose ports 80/443 publicly (keep it LAN/VPN-only), or
- Keep **Basic Auth enabled** (recommended), and avoid linking the site anywhere public.

### 2) Set Basic Auth (recommended)

Generate a bcrypt password hash:

```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'CHANGE_ME'
```

Create a `.env` file next to `docker-compose.prod.yml`:

```bash
BASIC_AUTH_USER=mc
BASIC_AUTH_HASH=$2a$12$...
```

### 3) Start

From repo root on the server:

```bash
cd deploy
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

### 4) “No Google detection” notes (important)

If a site is publicly reachable, you cannot guarantee it won’t be discovered
(links, certificate transparency, scanning). What we do here:
- `X-Robots-Tag: noindex` headers (strong hint)
- Optional **Basic Auth** (blocks crawlers entirely)

If you want near-zero risk, keep it **not publicly reachable**.


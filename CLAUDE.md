# Klikk (Tremly Property Manager)

Full-stack AI-powered property management platform for South African residential rental properties.
See `CONTEXT.md` for detailed technical architecture.

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `backend/` | Django 5 + DRF API, PostgreSQL |
| `admin/` | Vue 3 admin SPA (agent, supplier, owner portals) |
| `mobile/` | Flutter tenant app (iOS/Android) |
| `web_app/` | Vue 3 tenant web app |
| `tenant_app/` | Flutter tenant app (alternative) |
| `services/` | MCP servers (tremly-mcp for E2E testing) |
| `content/` | **Content hub — single source of truth for features, marketing, sales** |
| `website-preview/` | Approved static HTML design direction for marketing site |
| `website/` | Astro marketing website (when scaffolded) |

## Content Hub (`content/`)

The bidirectional bridge between development and marketing. Read `content/README.md` for conventions.

- **Feature status:** `content/product/features.yaml` — THE authority on what is built, in progress, or planned
- **Lifecycle:** `content/product/lifecycle.yaml` — 15-step rental journey, resolves status from features.yaml
- **Integrations:** `content/product/integrations.yaml` — third-party connections
- **Pricing:** `content/product/pricing.yaml` — tier definitions
- **Brand:** `content/brand/` — voice, positioning, competitive intel
- **Sales:** `content/sales/` — ICP, objections, demo flow
- **Website copy:** `content/website/copy/` — page-level marketing copy

### When you ship a feature

1. Update `content/product/features.yaml`: set `status: BUILT` and `shipped_date`
2. Optionally add a changelog entry in `content/changelog/`
3. That's it. Website badges update at next build.

### When you write marketing copy

1. Check `content/product/features.yaml` for current feature status
2. Never advertise PLANNED features as available
3. Follow `content/brand/voice.md` for tone and style

## Skills

| Skill | When to use |
|-------|-------------|
| `klikk-platform-product-status` | Check/update feature statuses, roadmap summaries |
| `klikk-marketing-website` | Build Astro website components, content-driven patterns |
| `klikk-marketing-strategy` | Write marketing copy, blog posts, campaigns |
| `klikk-marketing-sales-enablement` | Sales calls, demo prep, prospect research |
| `klikk-marketing-competitive-intel` | Competitive intelligence, market comparison, feature gaps |
| `klikk-design-standard` | Build/modify Vue admin UI |
| `klikk-design-mobile-ux` | Build/modify Quasar/Capacitor mobile UI (iOS HIG + Android MD3 specs) |
| `klikk-design-frontend-taste` | Senior UI/UX engineering, metric-based design rules |
| `klikk-leases-rental-agreement` | Generate SA lease agreements |
| `klikk-leases-tiptap-editor` | TipTap rich text editor for lease templates |
| `klikk-leases-pdf-export` | HTML-to-PDF pipeline, merge fields, signed PDF generation |
| `klikk-platform-gotenberg` | Gotenberg Docker PDF service, HTML/Office→PDF, merge/split/encrypt |
| `klikk-leases-format-template` | Format/restructure lease template HTML |
| `klikk-leases-parse-contract` | Parse PDF/DOCX lease into template with merge fields |
| `klikk-leases-test-battery` | Run full lease + e-signing integration test battery |
| `klikk-security-audit` | Security reviews |
| `klikk-security-auth-hardening` | Auth hardening, rate limiting, 2FA, JWT security |
| `klikk-security-api-review` | API endpoint security: auth, rate limiting, CORS, webhooks |
| `klikk-security-vuln-scan` | Django codebase vulnerability scan (SQLi, XSS, CSRF, IDOR) |
| `klikk-security-compliance` | POPIA/GDPR compliance checks |
| `klikk-security-user-model` | User model, roles, permissions security review |
| `klikk-platform-testing` | All testing work on the Tremly platform |
| `klikk-rental-master` | SA rental law knowledge base (RHA, PIE Act, deposits, eviction) |
| `klikk-property-stellenbosch-intel` | Scrape, enrich, classify, deduplicate and map Winelands properties |
| `klikk-property-municipal-bills` | Extract property data from SA municipal bills (tool_use pattern) |
| `klikk-documents-owner-cipro` | Classify SA owner/landlord docs (FICA/CIPRO/CIPC), extract fields, persons graph, mandate readiness |

## Conventions

- **South African context:** POPIA, RHA, ZAR, SA terminology throughout
- **Design tokens:** Navy (#2B2D6E), Accent (#FF3D7F) — see `klikk-design-standard` skill
- **Website design:** Bricolage Grotesque + DM Sans — see `klikk-marketing-website` skill
- **API base:** `http://localhost:8000/api/v1/`
- **Auth:** JWT (access + refresh tokens via simplejwt)
- **Admin frontend:** `http://localhost:5173/` (Vite dev server). If localhost:5173 is blank or curl returns an empty reply, **Cursor has likely bound 127.0.0.1:5173 for port forwarding** (same port as Vite). **Fix in Cursor (not in this repo):** press **Cmd+Shift+P** → run **“Ports: Focus on Ports View”** → in the **Ports** tab (bottom panel, next to Terminal), find **5173** → right‑click → **Stop Forwarding Port** (or **Change Local Port** and pick e.g. **15173** if you still need a tunnel). Then reload `http://localhost:5173/`. This can start after you **Forward a Port**, use **dev tunnels**, a **Cursor/VS Code update**, or **Remote / Dev Container** auto‑forward; `.vscode/settings.json` in this repo sets `onAutoForward: ignore` for 5173 in remote workflows only.

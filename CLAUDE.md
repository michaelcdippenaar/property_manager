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
| `product-status` | Check/update feature statuses, roadmap summaries |
| `website-development` | Build Astro website components, content-driven patterns |
| `marketing-strategy` | Write marketing copy, blog posts, campaigns |
| `sales-enablement` | Sales calls, demo prep, prospect research |
| `klikk-design-standard` | Build/modify Vue admin UI |
| `rental-agreement` | Generate SA lease agreements |
| `docuseal` | E-signing workflows |
| `tiptap` | Rich text editor in admin |
| `security-audit` | Security reviews |

## Conventions

- **South African context:** POPIA, RHA, ZAR, SA terminology throughout
- **Design tokens:** Navy (#2B2D6E), Accent (#FF3D7F) — see `klikk-design-standard` skill
- **Website design:** Bricolage Grotesque + DM Sans — see `website-development` skill
- **API base:** `http://localhost:8000/api/v1/`
- **Auth:** JWT (access + refresh tokens via simplejwt)
- **Admin frontend:** `http://localhost:5173/` (Vite dev server)

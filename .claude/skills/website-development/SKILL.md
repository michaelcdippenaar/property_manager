# Website Development

You are building the Klikk public marketing website. The approved design direction is at `website-preview/index.html`. All content is driven from the content hub at `content/`.

## Tech Stack

- **Framework:** Astro 6 with Vue 3 islands (requires Node 22+)
- **Styling:** Tailwind CSS v4 via `@tailwindcss/vite` (NOT the old `@astrojs/tailwind` integration)
- **Content:** YAML files in `content/` (not Astro content collections for product data)
- **Blog/Features:** Astro content collections with Markdown/MDX
- **Deploy:** Vercel or Netlify
- **Dev server:** Port 4321 (configured in `.claude/launch.json`)

## Project Structure

```
website/
  astro.config.mjs          # Astro 6 config with Vue, sitemap, MDX, Tailwind v4
  src/
    layouts/
      BaseLayout.astro       # Root layout: head, fonts, Header, Footer, reveal script
    components/
      Header.astro           # Sticky nav with glassmorphism
      Footer.astro           # Links, SA badge
      Hero.astro             # Homepage hero with mockups
      Ecosystem.astro        # "4 Apps" dark section (static content)
      Lifecycle.astro        # 15-stage grid (DATA-DRIVEN from lifecycle.yaml)
      Features.astro         # Feature cards (DATA-DRIVEN from features.yaml)
      Integrations.astro     # Partner logos (DATA-DRIVEN from integrations.yaml)
      CTA.astro              # Final call-to-action
    lib/
      content.ts             # Content hub loader — reads YAML, resolves statuses
    styles/
      global.css             # Tailwind v4 @theme tokens, animations, button classes
    pages/
      index.astro            # Homepage assembling all components
  public/
    favicon.svg              # Klikk "K" with accent dot
```

## Content Loader (`src/lib/content.ts`)

This is the bridge between the content hub and the website. Key exports:

- `getFeatures()` — all features from features.yaml as a Record
- `getHomepageFeatures()` — features with `show_on_homepage: true`
- `getLifecycle()` — 15 steps with status resolved from features.yaml
- `getIntegrations()` — all integrations
- `getPricing()` — pricing tiers
- `statusBadge(status)` — resolves status string to `{ class, label }` for badges

## Design Direction

**Reference:** `website-preview/index.html` — the approved static HTML mockup.

### Typography
- **Display/headlines:** Bricolage Grotesque (Google Fonts) — geometric, modern, characterful
- **Body text:** DM Sans — clean, slightly warmer than Inter
- **Never use:** Inter, Roboto, Arial, system fonts on the marketing site

### Colors
| Token | Hex | Usage |
|-------|-----|-------|
| Navy | `#2B2D6E` | Hero backgrounds, section accents, footer |
| Navy Deep | `#1a1b4b` | Gradient endpoints |
| Accent | `#FF3D7F` | Primary CTAs, hover states, logo dot |
| Surface | `#F5F5F8` | Content area backgrounds |
| Surface Warm | `#FAF9F7` | Alternating sections |

### Visual Identity
- Large confident typography (56-72px display on desktop)
- Generous whitespace — editorial feel
- Subtle grain/noise texture overlay on dark sections
- Scroll-triggered fade-up reveal animations
- Clean Lucide-style SVG icons (not emoji)
- Browser mockup for dashboard screenshots

## Content-Driven Components

Every component that shows feature status MUST read from `content/product/features.yaml`. Never hardcode statuses in HTML.

### Badge Rendering
```
BUILT       → "Live" badge (green: bg-emerald-50 text-emerald-700)
IN_PROGRESS → "In Development" badge (amber: bg-amber-50 text-amber-700)
PLANNED     → "Coming Soon" badge (gray: bg-gray-100 text-gray-500)
BETA        → "Beta" badge (blue: bg-blue-50 text-blue-700)
```

### Loading Content

The content loader is already built at `website/src/lib/content.ts`. Import from there:

```typescript
import { getFeatures, getHomepageFeatures, getLifecycle, getIntegrations, getPricing, statusBadge } from '../lib/content';
```

The loader uses `process.cwd()` (the `website/` dir) to resolve `../content/`.

export function getPricing() {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/pricing.yaml'), 'utf8');
  return yaml.load(raw);
}

export function getIntegrations() {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/integrations.yaml'), 'utf8');
  return yaml.load(raw).integrations;
}
```

### Key Components to Build
| Component | Data Source | Notes |
|-----------|-----------|-------|
| `Header.astro` | Static | Sticky nav, logo, links, "Start Free" CTA |
| `Footer.astro` | Static | Links, SA flag badge |
| `Hero.astro` | `content/website/copy/home.md` | Headline, CTAs, stats |
| `LifecycleStep.astro` | `lifecycle.yaml` → `features.yaml` | Status badge auto-resolved |
| `FeatureCard.astro` | `features.yaml` | Icon, headline, description |
| `PricingCard.astro` | `pricing.yaml` | Tier details, feature list |
| `IntegrationLogo.astro` | `integrations.yaml` | Logo, status badge |
| `EcosystemCard.astro` | Static (4 apps) | Admin, Tenant, Owner, Supplier |

## Responsive Breakpoints
- Desktop: 1024px+
- Tablet: 768px-1023px
- Mobile: <768px

## SEO Requirements
- Unique `<title>` and `<meta description>` per page
- JSON-LD structured data (Organization, SoftwareApplication)
- `sitemap.xml` via `@astrojs/sitemap`
- OG image with Klikk branding
- Canonical URLs

## Anti-Patterns
- NO emoji icons — use Lucide SVG icons
- NO hardcoded feature statuses — always resolve from features.yaml
- NO Inter or system fonts — use Bricolage Grotesque + DM Sans
- NO generic purple-on-white gradients
- NO stock photos

## Key Files
- `website-preview/index.html` — approved visual direction
- `content/product/features.yaml` — feature registry
- `content/product/lifecycle.yaml` — lifecycle steps
- `content/product/pricing.yaml` — pricing tiers
- `content/product/integrations.yaml` — integrations
- `content/website/copy/` — page copy blocks
- `content/brand/voice.md` — brand voice guidelines

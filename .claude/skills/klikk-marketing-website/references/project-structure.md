# Project Structure & Content Loader API

---

## Directory Layout

```
website/
  astro.config.mjs              # Astro 6 + Vue + sitemap + MDX + Tailwind v4
  src/
    layouts/
      BaseLayout.astro           # Root: HTML head, fonts, Header, Footer, scroll reveal
    components/
      Header.astro               # Sticky glassmorphism nav (5 links + Login CTA)
      Hero.astro                 # Full-viewport hero (headline, CTAs, mockups, stats)
      Ecosystem.astro            # "4 Apps, One Platform" bento grid
      Lifecycle.astro            # 15-stage rental lifecycle (DATA-DRIVEN)
      Features.astro             # AI feature cards grid (DATA-DRIVEN)
      Integrations.astro         # Dual-marquee partner carousel (DATA-DRIVEN)
      CTA.astro                  # Final call-to-action with trust badges
      Footer.astro               # Links, SA badge, copyright
    lib/
      content.ts                 # Content hub loader (reads YAML at build time)
    styles/
      global.css                 # Tailwind v4 @theme tokens, animations
    pages/
      index.astro                # Homepage (assembles all sections)
      pricing.astro              # Pricing page (4-tier grid + FAQ)
  public/
    favicon.svg                  # Klikk "K" with accent dot
    hero-bg.png                  # Dark textured hero background
    klikk-dashboard.png          # Admin dashboard screenshot (browser mockup)
    klikk-agent-app.png          # Agent app screenshot (phone mockup)
    og-image.png                 # Social share card
```

### Content Hub (`content/` at monorepo root)

```
content/
  product/
    features.yaml                # THE authority — 40+ features, status, lifecycle mapping
    lifecycle.yaml               # 15 rental stages + 11 sales stages
    integrations.yaml            # 6 integration partners
    pricing.yaml                 # 4-tier pricing model (ZAR)
  brand/
    voice.md                     # Brand voice guidelines
    positioning.md               # Market positioning, differentiators
  website/
    copy/                        # Page-specific copy blocks
```

---

## Content Loader API

**File:** `website/src/lib/content.ts`

All components import from this single loader. Reads YAML at build time.

| Export | Returns | Used By |
|--------|---------|---------|
| `getFeatures()` | `Record<string, Feature>` — all features keyed by ID | Lifecycle, Features |
| `getHomepageFeatures()` | `Feature[]` — features with `show_on_homepage: true` | Features.astro |
| `getLifecycle()` | `LifecycleStep[]` — 15 steps, status resolved from features | Lifecycle.astro |
| `getIntegrations()` | `Integration[]` — partner list | Integrations.astro |
| `getPricing()` | `{ tiers: PricingTier[], annual_discount: string }` | pricing.astro |
| `statusBadge(status)` | `{ class: string, label: string }` | All badge rendering |

### TypeScript Interfaces

```typescript
interface Feature {
  name: string; slug: string;
  status: 'BUILT' | 'IN_PROGRESS' | 'PLANNED' | 'BETA';
  shipped_date?: string;
  category: string; backend_app?: string; key_files?: string[];
  headline: string; tagline: string; description: string;
  icon: string;                    // Lucide icon name (e.g. "file-text")
  show_on_homepage?: boolean;      // true → appears in Features section
  homepage_section?: string;       // "features", "apps", "lifecycle"
  lifecycle_step?: number | null;  // 0-15 for rental lifecycle
}

interface LifecycleStep {
  step: number; title: string; description: string;
  feature_ref: string;             // Key into features.yaml
  status: Feature['status'];       // RESOLVED from features.yaml, never duplicated
  icon: string;                    // RESOLVED from features.yaml
}
```

### Status Badge Mapping

| Status | Badge Class | Label | Color |
|--------|-------------|-------|-------|
| `BUILT` | `built` | "Live" | Green (emerald) |
| `BETA` | `beta` | "Beta" | Blue |
| `IN_PROGRESS` | `in-progress` | "In Development" | Amber |
| `PLANNED` | `planned` | "Coming Soon" | Gray |

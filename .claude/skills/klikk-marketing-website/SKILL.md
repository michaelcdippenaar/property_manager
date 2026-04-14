---
name: klikk-marketing-website
description: >
  Build, update, and maintain the Klikk marketing website (Astro 6 + Tailwind v4 + Vue 3 islands).
  Content-driven architecture where features.yaml is the single source of truth for feature statuses,
  lifecycle badges, and homepage display. Covers: adding features, updating lifecycle stages, writing
  marketing copy, creating new pages, capturing screenshots, managing design tokens, and SEO.
  Load this skill when working on anything in website/, content/product/, content/brand/, or
  content/website/. Also load when the user asks about the marketing site, landing page, or
  website copy.
---

# Klikk Marketing Website Development

**Stack:** Astro 6 + Vue 3 islands + Tailwind CSS v4 + js-yaml
**Node:** 22.12.0+ required
**Dev server:** Port 4321 (`Klikk Website (Astro dev)` in launch.json)
**Content hub:** `content/` at monorepo root (YAML = single source of truth)
**Content loader:** `website/src/lib/content.ts` (bridge between YAML and components)

---

## MANDATE

When building or updating the marketing website:

1. **Never hardcode feature statuses** — always resolve from `content/product/features.yaml`
2. **Never duplicate status** — lifecycle.yaml references features via `feature_ref`, status resolves at render
3. **Never use emoji** — use Lucide SVG icons everywhere
4. **Never use Inter/Roboto/system fonts** — Bricolage Grotesque (display) + DM Sans (body) only
5. **Follow brand voice** — see `content/brand/voice.md` (smart colleague, not corporate consultant)
6. **SA-first always** — RHA, POPIA, ZAR, SA terminology, "favour" not "favor"
7. **Never advertise PLANNED features as available** — Coming Soon badge only

---

## Part 1: Project Structure

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

### Content Hub (monorepo root)

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
    competitors.md               # Competitive landscape
    marketing-ideas.md           # Campaign activation ideas
  website/
    copy/                        # Page-specific copy blocks
```

---

## Part 2: Content Loader API

**File:** `website/src/lib/content.ts`

All components import from this single loader. It reads YAML at build time.

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

---

## Part 3: Design System

### Typography

| Role | Font | Weight | Size (desktop) |
|------|------|--------|----------------|
| Display/H1 | Bricolage Grotesque | 800 | 56-72px |
| H2 section titles | Bricolage Grotesque | 800 | 36-44px |
| H3 card titles | DM Sans | 600 | 18-20px |
| Body | DM Sans | 400 | 16-17px |
| Caption/labels | DM Sans | 500-600 | 11-14px |

### Color Tokens (`global.css` @theme)

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-navy` | `#2B2D6E` | Hero, dark sections, footer |
| `--color-navy-deep` | `#1a1b4b` | Gradient endpoints, overlays |
| `--color-navy-light` | `#3b3e8f` | Subtle navy variation |
| `--color-accent` | `#FF3D7F` | Primary CTAs, logo dot, highlights |
| `--color-accent-light` | `#FF6B9D` | Gradient start points |
| `--color-accent-dark` | `#E02D6B` | Hover/active states |
| `--color-surface` | `#F5F5F8` | Light content backgrounds |
| `--color-surface-warm` | `#FAF9F7` | Alternating sections |
| `--color-success` | `#10b981` | "Live" badges, success states |

### Animations

| Animation | Duration | Usage |
|-----------|----------|-------|
| `fadeUp` | 0.8s ease-out | Staggered section reveals (`.fade-up-1` through `.fade-up-5`) |
| `float` | 6s ease-in-out infinite | Floating phone mockup in Hero |
| `scrollLeft` | 60s linear infinite | Integration marquee carousel |
| `pulse-dot` | 2s ease-in-out infinite | Green status dot on badges |

### Scroll Reveal

```css
.reveal { opacity: 0; transform: translateY(28px); }
.reveal.visible { animation: fadeUp 0.8s ease-out forwards; }
```

Intersection Observer in BaseLayout.astro fires `.visible` class on scroll. Use `.reveal-delay-1` through `.reveal-delay-6` for stagger (40-80ms apart).

### Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop | ≥1100px | Full multi-column grids |
| Tablet | 768-1099px | Reduced columns |
| Mobile | <768px | Single column, stacked |

---

## Part 4: Common Tasks

### Task A: Ship a Feature (Update Lifecycle Badge)

When a feature is built:

1. **Edit `content/product/features.yaml`:**
   ```yaml
   property_viewings:
     status: BUILT            # Was: PLANNED
     shipped_date: 2026-04-11 # Was: null
   ```

2. **That's it.** The lifecycle component auto-resolves:
   - `Lifecycle.astro` calls `getLifecycle()` → `content.ts` reads features.yaml
   - The step's `feature_ref` matches the feature → status becomes `BUILT`
   - Badge renders as "Live" (green) instead of "Coming Soon" (gray)

3. Restart Astro dev server if running (YAML changes require rebuild)

### Task B: Add a New Feature to Homepage

1. **Add/update entry in `content/product/features.yaml`:**
   ```yaml
   agent_mobile_app:
     name: "Klikk Agent App"
     slug: agent-mobile-app
     status: BUILT
     shipped_date: 2026-04-11
     product: rentals
     category: apps
     headline: "Agent Mobile App"
     tagline: "Manage properties and viewings on the go"
     description: >
       Native iOS and Android app for rental agents...
     icon: smartphone              # Lucide icon name
     show_on_homepage: true         # REQUIRED for homepage display
     homepage_section: features     # "features", "apps", or "lifecycle"
     lifecycle_step: null
   ```

2. Features.astro filters by `show_on_homepage: true` and `homepage_section: 'features'`
3. The component auto-renders the card with icon, headline, description, and status badge

### Task C: Add a New Lifecycle Stage

1. **Add step to `content/product/lifecycle.yaml`:**
   ```yaml
   rental_lifecycle:
     - step: 16
       title: "Handover"
       description: "Keys, meters, and move-in checklist"
       feature_ref: move_in_handover    # Must match a key in features.yaml
   ```

2. **Add matching feature in `content/product/features.yaml`:**
   ```yaml
   move_in_handover:
     status: PLANNED
     # ... all required fields
   ```

### Task D: Update Hero Screenshots

**Admin Dashboard (browser mockup):**
1. Start Django API: `preview_start` → "Django API (local venv)"
2. Start Admin SPA: `preview_start` → "Admin SPA (Vite)"
3. Use puppeteer to capture authenticated screenshot:
   - Login via API: `POST /api/v1/auth/login/` with credentials
   - Set `localStorage.access_token` and `localStorage.refresh_token`
   - Navigate to `http://localhost:5173/`
   - Screenshot to `website/public/klikk-dashboard.png`
4. Hero.astro references: `<img src="/klikk-dashboard.png" />`

**Agent App (phone mockup):**
1. Capture from iOS simulator: `xcrun simctl io booted screenshot /path/to/file.png`
2. Crop to screen content only using `sips`:
   ```bash
   sips --cropToHeightWidth HEIGHT WIDTH --cropOffset Y X source.png --out klikk-agent-app.png
   ```
3. Save to `website/public/klikk-agent-app.png`
4. Hero.astro renders it inside a floating phone frame (`.phone-mockup`)

### Task E: Add a New Page

```astro
---
// website/src/pages/about.astro
import BaseLayout from '../layouts/BaseLayout.astro';
---
<BaseLayout title="About Klikk" description="The story behind Klikk property management.">
  <section class="section-light">
    <div class="container">
      <h1>About Klikk</h1>
      <!-- Content -->
    </div>
  </section>
</BaseLayout>
```

- BaseLayout provides: HTML head, fonts, Header, Footer, scroll reveal script
- Add nav link in Header.astro if needed
- Follow existing section patterns (`.section-dark`, `.section-light`)

### Task F: Update Pricing

Edit `content/product/pricing.yaml`:
```yaml
tiers:
  - name: Starter
    slug: starter
    units: "1-5"
    price: "Free"
    price_numeric: 0
    billing: "forever"
    highlight: false
    features:
      - "Up to 5 units"
      - "1 user"
    cta_text: "Start Free"
    cta_url: "/register"
annual_discount: "15%"
```

### Task G: Add an Integration

Edit `content/product/integrations.yaml`:
```yaml
integrations:
  whatsapp:
    name: "WhatsApp Business"
    slug: whatsapp
    status: PLANNED
    category: communication
    tagline: "Tenant messaging via WhatsApp"
    logo_abbrev: "WA"
    logo_color: "#25D366"
    description: "Send lease updates and maintenance alerts via WhatsApp."
```

---

## Part 5: Component Reference

### Hero.astro
- Full-viewport, 2-column (content + visual) at ≥1100px
- Browser mockup: `<img src="/klikk-dashboard.png" />` inside `.hero-mockup`
- Phone mockup: `<img src="/klikk-agent-app.png" />` inside `.phone-mockup` (absolute positioned, floating animation)
- 3 stats at bottom: lifecycle stages, apps count, lease generation time
- Responsive: stacks to single column, phone hidden on mobile

### Lifecycle.astro
- Dark section (background `#0f1038`)
- 5-column grid (tablet: 3, mobile: 2)
- Each step: number circle, title, description, status badge
- Built steps get green tint, green badge ("Live")
- Planned steps get gray badge ("Coming Soon")
- Data: `getLifecycle()` → resolves status from features.yaml

### Features.astro
- Light section (surface warm)
- 3-column grid (tablet: 2, mobile: 1)
- Each card: colored icon, headline, description, status badge, hover lift
- Icons cycle through a 6-color palette
- Filter: `features.filter(f => f.homepage_section === 'features')`

### Ecosystem.astro
- Dark section
- Bento grid: Admin (tall), Tenant, Owner, Supplier (stretch)
- Static content (4 apps are fixed)
- Platform badges (Web, iOS, Android)

### Integrations.astro
- Dual marquee: Row 1 scrolls left, Row 2 scrolls right (reversed)
- 60s infinite loop, fade masks on edges
- Each card: logo circle, name, tagline, "Live" badge if BUILT

### CTA.astro
- Dark gradient with radial accent glow
- Two CTAs: "Start Free Today" (primary), "Talk to Us" (ghost)
- Trust badges: SA flag, POPIA, RHA

---

## Part 6: Brand Voice Quick Reference

**Tone:** Professional but approachable ("smart colleague")

| Do | Don't |
|----|-------|
| "AI generates your lease" | "Leveraging artificial intelligence..." |
| "Built for the Rental Housing Act" | "Compliance-first regulatory framework" |
| "Free for up to 5 units" | "Freemium tier with limited access" |
| "Connect your PayProp account" | "Integrate with payment providers" |

**Copy rules:**
- Short, punchy — property managers are busy
- SA context always (RHA, POPIA, PayProp, Property24 by name)
- Honest about status — never imply PLANNED features are available
- Technical confidence without jargon (mention Claude AI, WebSockets, Flutter)

---

## Part 7: SEO Requirements

- Unique `<title>` and `<meta description>` per page
- JSON-LD structured data (Organization, SoftwareApplication)
- `sitemap.xml` via `@astrojs/sitemap` (configured in astro.config.mjs)
- OG image: `website/public/og-image.png`
- Canonical URLs on all pages

---

## Part 8: Anti-Patterns

| Never Do | Instead |
|----------|---------|
| Hardcode feature status in HTML | Read from features.yaml via content.ts |
| Use emoji icons | Use Lucide SVG icons |
| Use Inter, Roboto, or system fonts | Bricolage Grotesque + DM Sans |
| Use generic stock photos | Use real product screenshots |
| Duplicate status in lifecycle.yaml | Reference via `feature_ref`, resolve in content.ts |
| Skip mobile responsiveness | Every component must have mobile/tablet/desktop |
| Use `@astrojs/tailwind` | Use `@tailwindcss/vite` (Tailwind v4) |
| Put secrets in public/ | Only static assets in public/ |

---

## Part 9: Key Files Reference

| Purpose | File |
|---------|------|
| Feature registry (source of truth) | `content/product/features.yaml` |
| Lifecycle stages | `content/product/lifecycle.yaml` |
| Pricing tiers | `content/product/pricing.yaml` |
| Integration partners | `content/product/integrations.yaml` |
| Brand voice | `content/brand/voice.md` |
| Market positioning | `content/brand/positioning.md` |
| Content loader (YAML → components) | `website/src/lib/content.ts` |
| Design tokens | `website/src/styles/global.css` |
| Homepage assembly | `website/src/pages/index.astro` |
| Astro config | `website/astro.config.mjs` |
| Dev server config | `.claude/launch.json` ("Klikk Website (Astro dev)") |
| Approved design direction | `website-preview/index.html` |

---

## Part 10: Troubleshooting

| Issue | Fix |
|-------|-----|
| YAML changes not reflected | Restart Astro dev server (YAML read at build time) |
| "Content config not loaded" warning | Safe to ignore — we use custom YAML loader, not Astro content collections |
| New feature not showing on homepage | Check `show_on_homepage: true` AND `homepage_section: 'features'` |
| Lifecycle badge still "Coming Soon" | Ensure the feature's `status` in features.yaml is `BUILT`, not just lifecycle.yaml |
| Fonts not loading | Check Google Fonts link in BaseLayout.astro `<head>` |
| Node version error | Requires Node 22.12.0+ (check `.nvmrc` or `package.json` engines) |
| Tailwind classes not applying | Using Tailwind v4 with `@tailwindcss/vite`, not the old Astro integration |
| Preview screenshots blank after scroll | Known issue with preview tool — restart server or verify via DOM eval |

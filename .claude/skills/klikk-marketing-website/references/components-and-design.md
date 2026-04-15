# Design System & Component Reference

---

## Typography

| Role | Font | Weight | Size (desktop) |
|------|------|--------|----------------|
| Display/H1 | Bricolage Grotesque | 800 | 56-72px |
| H2 section titles | Bricolage Grotesque | 800 | 36-44px |
| H3 card titles | DM Sans | 600 | 18-20px |
| Body | DM Sans | 400 | 16-17px |
| Caption/labels | DM Sans | 500-600 | 11-14px |

---

## Color Tokens (`global.css` @theme)

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

---

## Animations

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
Intersection Observer fires `.visible` on scroll. Use `.reveal-delay-1` through `.reveal-delay-6` for stagger.

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop | ≥1100px | Full multi-column grids |
| Tablet | 768-1099px | Reduced columns |
| Mobile | <768px | Single column, stacked |

---

## Component Reference

### Hero.astro
- Full-viewport, 2-column (content + visual) at ≥1100px
- Browser mockup: `<img src="/klikk-dashboard.png" />` inside `.hero-mockup`
- Phone mockup: `<img src="/klikk-agent-app.png" />` inside `.phone-mockup` (floating animation)
- 3 stats at bottom: lifecycle stages, apps count, lease generation time
- Responsive: stacks to single column, phone hidden on mobile

### Lifecycle.astro
- Dark section (background `#0f1038`), 5-column grid (tablet: 3, mobile: 2)
- Built steps get green tint + "Live" badge; Planned get "Coming Soon"
- Data: `getLifecycle()` → resolves status from features.yaml

### Features.astro
- Light section (surface warm), 3-column grid (tablet: 2, mobile: 1)
- Icons cycle through a 6-color palette
- Filter: `features.filter(f => f.homepage_section === 'features')`

### Ecosystem.astro
- Dark section, bento grid: Admin (tall), Tenant, Owner, Supplier (stretch)
- Static content (4 apps are fixed), Platform badges (Web, iOS, Android)

### Integrations.astro
- Dual marquee: Row 1 scrolls left, Row 2 scrolls right (reversed), 60s loop
- Each card: logo circle, name, tagline, "Live" badge if BUILT

### CTA.astro
- Dark gradient with radial accent glow
- Two CTAs: "Start Free Today" (primary), "Talk to Us" (ghost)
- Trust badges: SA flag, POPIA, RHA

---

## SEO Requirements

- Unique `<title>` and `<meta description>` per page
- JSON-LD structured data (Organization, SoftwareApplication)
- `sitemap.xml` via `@astrojs/sitemap` (configured in `astro.config.mjs`)
- OG image: `website/public/og-image.png`
- Canonical URLs on all pages

---

## Anti-Patterns

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

## Key Files

| Purpose | File |
|---------|------|
| Feature registry (source of truth) | `content/product/features.yaml` |
| Lifecycle stages | `content/product/lifecycle.yaml` |
| Pricing tiers | `content/product/pricing.yaml` |
| Integration partners | `content/product/integrations.yaml` |
| Brand voice | `content/brand/voice.md` |
| Content loader (YAML → components) | `website/src/lib/content.ts` |
| Design tokens | `website/src/styles/global.css` |
| Homepage assembly | `website/src/pages/index.astro` |
| Astro config | `website/astro.config.mjs` |
| Dev server config | `.claude/launch.json` ("Klikk Website (Astro dev)") |
| Approved design direction | `website-preview/index.html` |

# Common Tasks

---

## Task A: Ship a Feature (Update Lifecycle Badge)

1. **Edit `content/product/features.yaml`:**
   ```yaml
   property_viewings:
     status: BUILT            # Was: PLANNED
     shipped_date: 2026-04-11 # Was: null
   ```
2. **That's it.** Lifecycle auto-resolves via `feature_ref` → `BUILT` → renders "Live" badge.
3. Restart Astro dev server (YAML changes require rebuild).

---

## Task B: Add a New Feature to Homepage

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
2. Features.astro filters by `show_on_homepage: true` and `homepage_section: 'features'`.

---

## Task C: Add a New Lifecycle Stage

1. Add step to `content/product/lifecycle.yaml`:
   ```yaml
   rental_lifecycle:
     - step: 16
       title: "Handover"
       description: "Keys, meters, and move-in checklist"
       feature_ref: move_in_handover
   ```
2. Add matching feature in `content/product/features.yaml`:
   ```yaml
   move_in_handover:
     status: PLANNED
     # ... all required fields
   ```

---

## Task D: Update Hero Screenshots

**Admin Dashboard (browser mockup):**
1. Start Django API + Admin SPA
2. Login via API: `POST /api/v1/auth/login/`
3. Set `localStorage.access_token` and `localStorage.refresh_token`
4. Navigate to `http://localhost:5173/` and screenshot → `website/public/klikk-dashboard.png`

**Agent App (phone mockup):**
1. Capture from iOS simulator: `xcrun simctl io booted screenshot /path/to/file.png`
2. Crop: `sips --cropToHeightWidth HEIGHT WIDTH --cropOffset Y X source.png --out klikk-agent-app.png`
3. Save to `website/public/klikk-agent-app.png`

---

## Task E: Add a New Page

```astro
---
// website/src/pages/about.astro
import BaseLayout from '../layouts/BaseLayout.astro';
---
<BaseLayout title="About Klikk" description="The story behind Klikk property management.">
  <section class="section-light">
    <div class="container">
      <h1>About Klikk</h1>
    </div>
  </section>
</BaseLayout>
```

- Add nav link in `Header.astro` if needed
- Follow existing section patterns (`.section-dark`, `.section-light`)

---

## Task F: Update Pricing

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

---

## Task G: Add an Integration

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

## Troubleshooting

| Issue | Fix |
|-------|-----|
| YAML changes not reflected | Restart Astro dev server (YAML read at build time) |
| "Content config not loaded" warning | Safe to ignore — using custom YAML loader, not Astro content collections |
| New feature not on homepage | Check `show_on_homepage: true` AND `homepage_section: 'features'` |
| Lifecycle badge still "Coming Soon" | Ensure `status: BUILT` in features.yaml (not just lifecycle.yaml) |
| Fonts not loading | Check Google Fonts link in `BaseLayout.astro <head>` |
| Node version error | Requires Node 22.12.0+ |
| Tailwind classes not applying | Using Tailwind v4 with `@tailwindcss/vite`, not old Astro integration |

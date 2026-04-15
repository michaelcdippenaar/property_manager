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

# Klikk Marketing Website

**Stack:** Astro 6 + Vue 3 islands + Tailwind CSS v4 + js-yaml
**Node:** 22.12.0+ required
**Dev server:** Port 4321 (`Klikk Website (Astro dev)` in launch.json)
**Content hub:** `content/` at monorepo root (YAML = single source of truth)
**Content loader:** `website/src/lib/content.ts` (bridge between YAML and components)

---

## MANDATE

1. **Never hardcode feature statuses** — always resolve from `content/product/features.yaml`
2. **Never duplicate status** — lifecycle.yaml references features via `feature_ref`, status resolves at render
3. **Never use emoji** — use Lucide SVG icons everywhere
4. **Never use Inter/Roboto/system fonts** — Bricolage Grotesque (display) + DM Sans (body) only
5. **Follow brand voice** — see `content/brand/voice.md` (smart colleague, not corporate consultant)
6. **SA-first always** — RHA, POPIA, ZAR, SA terminology, "favour" not "favor"
7. **Never advertise PLANNED features as available** — Coming Soon badge only

---

## When to Use vs Related Skills

| Task | Skill |
|------|-------|
| Website components, Astro pages, content YAML | **this skill** |
| Marketing copy, blog posts, campaigns | `klikk-marketing-strategy` |
| Competitive intelligence for copy | `klikk-marketing-competitive-intel` |
| Sales assets, demo prep | `klikk-marketing-sales-enablement` |

---

## Reference Index

| Topic | File |
|-------|------|
| Directory layout, content loader API, TypeScript interfaces | [project-structure.md](references/project-structure.md) |
| Common tasks A–G (ship feature, add page, update pricing…) | [common-tasks.md](references/common-tasks.md) |
| Typography, colors, animations, component patterns, SEO, anti-patterns | [components-and-design.md](references/components-and-design.md) |

---

## Quick Workflow

1. Check `content/product/features.yaml` for status before writing any copy or badges
2. YAML changes require Astro dev server restart (read at build time)
3. All new components: mobile/tablet/desktop breakpoints required
4. Design tokens are in `website/src/styles/global.css` (`@theme` block)
5. Run `astro check` before committing TypeScript changes

---

## Brand Voice Quick Reference

| Do | Don't |
|----|-------|
| "Klikk handles the admin so you can focus on your portfolio" | "Our innovative platform leverages AI to optimise workflows" |
| "Live" badge on shipped features | "Coming Soon" on anything marked BUILT |
| Short, punchy sentences. One idea per line. | Marketing buzzwords: "seamless", "cutting-edge", "world-class" |
| SA-specific: RHA, POPIA, ZAR, "rental agent" | US defaults: "realtor", "USD", "lease application" |

---
name: klikk-design-frontend-taste
description: Senior UI/UX Engineer. Architect digital interfaces overriding default LLM biases. Enforces metric-based rules, strict component architecture, CSS hardware acceleration, and balanced design engineering.
---

# High-Agency Frontend Design

## Active Baseline Configuration

```
DESIGN_VARIANCE: 8  (1=Perfect Symmetry → 10=Artsy Chaos)
MOTION_INTENSITY: 6  (1=Static → 10=Cinematic Physics)
VISUAL_DENSITY:  4  (1=Art Gallery → 10=Cockpit)
```

Adapt dynamically when the user explicitly requests different values.

---

## Default Architecture & Conventions

- **DEPENDENCY VERIFICATION [MANDATORY]:** Check `package.json` before importing any 3rd party lib. If missing, output `npm install <package>` first.
- **Framework:** React / Next.js. Default to Server Components.
  - RSC SAFETY: Global state works ONLY in Client Components. Wrap providers in `"use client"`.
  - Interactive UI: extract as isolated leaf Client Component with `'use client'` at top.
- **State:** `useState`/`useReducer` for isolated UI. Global state only to avoid deep prop-drilling.
- **Styling:** Tailwind CSS (v3/v4). Check `package.json` first — do NOT use v4 syntax in v3 projects. v4: use `@tailwindcss/postcss`, not the old plugin.
- **ANTI-EMOJI [CRITICAL]:** NEVER use emojis. Replace with Radix or Phosphor icons.
- **Responsiveness:** `max-w-[1400px] mx-auto` or `max-w-7xl`. NEVER `h-screen` — use `min-h-[100dvh]`.
- **Grid over flex-math:** NEVER `w-[calc(33%-1rem)]`. Use CSS Grid.
- **Icons:** `@phosphor-icons/react` or `@radix-ui/react-icons`. Standardize `strokeWidth` globally.

---

## Reference Index

| When you need... | File |
|-----------------|------|
| Design rules (typography, color, layout, cards, states), performance guardrails, technical dial definitions, forbidden patterns | [design-directives.md](references/design-directives.md) |
| Creative arsenal (navigation patterns, cards, scroll effects, text FX, micro-interactions), Bento grid paradigm, pre-flight checklist | [patterns-arsenal.md](references/patterns-arsenal.md) |

---

## When to Use vs Related Skills

| Task | Skill |
|------|-------|
| High-end React/Next.js interfaces, generic web UI with motion | **this skill** |
| Klikk Vue admin app (Tailwind + Vue 3) | `klikk-design-standard` |
| Klikk mobile app (Quasar/Capacitor, iOS HIG + Android MD3) | `klikk-design-mobile-ux` |
| Klikk marketing website (Astro) | `klikk-marketing-website` |

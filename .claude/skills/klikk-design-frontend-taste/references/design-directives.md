# Design Directives, Performance & Technical Reference

---

## Design Engineering Directives (Bias Correction)

### Rule 1: Deterministic Typography
- **Display/Headlines:** `text-4xl md:text-6xl tracking-tighter leading-none`
- **Anti-Slop fonts:** Use `Geist`, `Outfit`, `Cabinet Grotesk`, or `Satoshi` — never `Inter`
- **Dashboard UIs:** Serif fonts BANNED — use high-end Sans-Serif only (`Geist` + `Geist Mono`)
- **Body/Paragraphs:** `text-base text-gray-600 leading-relaxed max-w-[65ch]`

### Rule 2: Color Calibration
- Max 1 Accent Color; Saturation < 80%
- **THE LILA BAN:** AI Purple/Blue aesthetic BANNED. No purple button glows, no neon gradients
- Use absolute neutral bases (Zinc/Slate) with high-contrast singular accents (Emerald, Electric Blue, Deep Rose)
- Stick to one palette for the entire output (no warm/cool mixing)

### Rule 3: Layout Diversification
- **ANTI-CENTER BIAS:** Centered Hero/H1 BANNED when `DESIGN_VARIANCE > 4`
- Force "Split Screen" (50/50), "Left content / Right asset", or "Asymmetric White-space"

### Rule 4: Materiality — Anti-Card Overuse
- **DASHBOARD HARDENING (`VISUAL_DENSITY > 7`):** Generic card containers BANNED — use `border-t`, `divide-y`, or negative space
- Use cards ONLY when elevation communicates hierarchy. Tint shadows to background hue.

### Rule 5: Interactive UI States
Implement full interaction cycles — never generate only the "success" state:
- **Loading:** Skeletal loaders matching layout sizes
- **Empty States:** Beautifully composed empty states showing how to populate data
- **Error States:** Clear, inline error reporting
- **Tactile Feedback:** On `:active`, use `-translate-y-[1px]` or `scale-[0.98]`

### Rule 6: Data & Form Patterns
- Labels sit ABOVE inputs; helper text optional; error text below input; `gap-2` for input blocks

---

## Creative Proactivity (Anti-Slop Implementation)

- **Liquid Glass:** Beyond `backdrop-blur` — add `border-white/10` inner border + `shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`
- **Magnetic Micro-physics (`MOTION_INTENSITY > 5`):** Use `useMotionValue` + `useTransform` (NEVER `useState`) for magnetic hover
- **Perpetual Micro-Interactions (`MOTION_INTENSITY > 5`):** Pulse, Typewriter, Float, Shimmer — Spring Physics: `type: "spring", stiffness: 100, damping: 20`
- **Layout Transitions:** Always use Framer Motion `layout` and `layoutId` props
- **Staggered Orchestration:** `staggerChildren` or CSS `animation-delay: calc(var(--index) * 100ms)`. Parent and Children must be in the SAME Client Component tree.

---

## Performance Guardrails

- **DOM Cost:** Grain/noise filters ONLY on `fixed inset-0 z-50 pointer-events-none` pseudo-elements — NEVER on scrolling containers
- **Hardware Acceleration:** Animate ONLY via `transform` and `opacity` — NEVER `top`, `left`, `width`, `height`
- **Z-Index Restraint:** NEVER spam `z-50` arbitrarily — only for systemic layers (navbars, modals, overlays)

---

## Technical Reference — Dial Definitions

### DESIGN_VARIANCE (1–10)
- **1–3 (Predictable):** `justify-center`, strict 12-col symmetric grids, equal paddings
- **4–7 (Offset):** `margin-top: -2rem` overlapping, varied aspect ratios, left-aligned headers over center data
- **8–10 (Asymmetric):** Masonry layouts, `grid-template-columns: 2fr 1fr 1fr`, `padding-left: 20vw`
- **MOBILE OVERRIDE (4–10):** Any asymmetric layout MUST fall back to strict single-column on `< 768px`

### MOTION_INTENSITY (1–10)
- **1–3 (Static):** CSS `:hover`/`:active` only
- **4–7 (Fluid CSS):** `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`. `will-change: transform` sparingly
- **8–10 (Advanced):** Framer Motion hooks. NEVER `window.addEventListener('scroll')`

### VISUAL_DENSITY (1–10)
- **1–3 (Art Gallery):** Massive white space. Expensive and clean.
- **4–7 (Daily App):** Normal web app spacing
- **8–10 (Cockpit):** Tiny paddings, 1px dividers, no cards, `font-mono` for all numbers

---

## AI Tells — Forbidden Patterns

### Visual & CSS
- NO neon outer glows (use inner borders or tinted shadows)
- NO pure `#000000` (use Zinc-950 or Charcoal)
- NO oversaturated accents
- NO excessive gradient text on large headers
- NO custom mouse cursors

### Typography
- NO Inter font (use `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`)
- NO oversized H1s — control hierarchy with weight/color, not scale
- NO serif on dashboards

### Layout & Spacing
- Padding and margins must be mathematically perfect
- NO 3-column equal card layouts — use 2-col Zig-Zag, asymmetric grid, or horizontal scroll

### Content & Data
- NO "John Doe", "Sarah Chan" — use creative realistic names
- NO generic SVG "egg" avatars
- NO fake numbers like `99.99%` or `1234567` — use organic data (`47.2%`, `+1 (312) 847-1928`)
- NO startup slop names: "Acme", "Nexus", "SmartFlow"
- NO filler words: "Elevate", "Seamless", "Unleash", "Next-Gen"

### External Resources
- NO Unsplash (broken links). Use `https://picsum.photos/seed/{random_string}/800/600`
- `shadcn/ui` must be customized — NEVER default state

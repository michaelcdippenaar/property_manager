# Creative Arsenal & Bento Paradigm

---

## Creative Arsenal — High-End Patterns

### Navigation & Menus
- **Mac OS Dock Magnification:** Nav icons scale fluidly on hover
- **Magnetic Button:** Buttons physically pull toward the cursor
- **Dynamic Island:** Pill-shaped UI that morphs to show status/alerts
- **Mega Menu Reveal:** Full-screen dropdowns that stagger-fade complex content

### Layout & Grids
- **Bento Grid:** Asymmetric tile-based grouping (Apple Control Center)
- **Masonry Layout:** Staggered grid without fixed row heights
- **Chroma Grid:** Grid borders/tiles with continuously animating color gradients
- **Split Screen Scroll:** Two screen halves sliding in opposite directions
- **Curtain Reveal:** Hero section parting in the middle on scroll

### Cards & Containers
- **Parallax Tilt Card:** 3D-tilting card tracking mouse coordinates
- **Spotlight Border Card:** Card borders illuminate under the cursor
- **Glassmorphism Panel:** True frosted glass with inner refraction borders
- **Morphing Modal:** Button expands seamlessly into full-screen dialog

### Scroll Animations
- **Sticky Scroll Stack:** Cards stick to top and physically stack over each other
- **Horizontal Scroll Hijack:** Vertical scroll → smooth horizontal gallery pan
- **Zoom Parallax:** Background image zooms in/out on scroll
- **Scroll Progress Path:** SVG lines draw themselves as user scrolls

### Typography & Text
- **Kinetic Marquee:** Endless text bands that reverse direction or speed up
- **Text Scramble Effect:** Matrix-style character decoding on load/hover
- **Gradient Stroke Animation:** Outlined text with a running gradient along the stroke

### Micro-Interactions & Effects
- **Particle Explosion Button:** CTAs shatter into particles on success
- **Skeleton Shimmer:** Shifting light reflections on placeholder boxes
- **Directional Hover Aware Button:** Fill enters from the side the mouse entered
- **Mesh Gradient Background:** Organic lava-lamp animated color blobs

---

## Motion Engine Bento Paradigm (SaaS Dashboards)

### Core Design Philosophy
- **Aesthetic:** High-end, minimal, functional
- **Palette:** Background `#f9fafb`, cards pure white `#ffffff` with `border-slate-200/50`
- **Surfaces:** `rounded-[2.5rem]` + "diffusion shadow" `shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)]`
- **Typography:** Strict `Geist`, `Satoshi`, or `Cabinet Grotesk` + `tracking-tight`
- **Labels:** Titles/descriptions placed OUTSIDE and BELOW cards
- **Padding:** Generous `p-8` or `p-10` inside cards

### Animation Engine Specs
All cards must have **Perpetual Micro-Interactions:**
- Spring Physics: `type: "spring", stiffness: 100, damping: 20`
- `layout` and `layoutId` props for smooth re-ordering
- Every card must loop infinitely (Pulse, Typewriter, Float, or Carousel)
- Wrap dynamic lists in `<AnimatePresence>`
- **CRITICAL:** Perpetual motion/infinite loops MUST be `React.memo` and isolated in their own Client Component

### The 5 Bento Card Archetypes
1. **Intelligent List:** Infinite auto-sort; items swap with `layoutId` simulating AI prioritization
2. **Command Input:** Multi-step Typewriter Effect cycling through complex prompts + blinking cursor
3. **Live Status:** "Breathing" status indicators; notification badge with Overshoot spring, stays 3s then vanishes
4. **Wide Data Stream:** Horizontal Infinite Carousel; seamless loop `x: ["0%", "-100%"]`
5. **Contextual UI (Focus Mode):** Staggered text highlight + Float-in floating action toolbar

---

## Pre-flight Checklist (Run Before Every Output)

- [ ] Global state used to avoid deep prop-drilling, not arbitrarily?
- [ ] Mobile layout collapse (`w-full`, `px-4`, `max-w-7xl mx-auto`) for high-variance designs?
- [ ] Full-height sections use `min-h-[100dvh]` instead of `h-screen`?
- [ ] `useEffect` animations have strict cleanup functions?
- [ ] Empty, loading, and error states provided?
- [ ] Cards omitted in favor of spacing where possible?
- [ ] CPU-heavy perpetual animations isolated in own Client Components?

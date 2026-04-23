---
name: klikk-marketing-brand-assets
description: >
  Brand token enforcement + Remotion/Higgsfield creative conventions for Klikk video, carousel,
  PDF, image-gen prompt assets. Loads when brand-creative agent produces assets.
---

# Brand Assets

## Tokens (enforce everywhere)

| Token | Value |
|---|---|
| Navy | `#2B2D6E` |
| Accent pink | `#FF3D7F` |
| White | `#FFFFFF` |
| Grey | `#9A9AB0` |
| Font stack | `"Bricolage Grotesque", "DM Sans", -apple-system, sans-serif` |

Any asset using different colours or fonts is off-brand unless brief explicitly permits.

## Before creating anything — read

- `marketing/brand/voice.md` — tone
- `marketing/brand/positioning.md` — what to emphasise
- `my-video/src/` — reuse existing Remotion components
- `content/product/features.yaml` — never visualise unshipped features

## Output folders

| Asset | Folder |
|---|---|
| Remotion source | `my-video/src/` |
| B-roll AI clips | `my-video/public/broll/` |
| Image-gen prompts | `marketing/creative/prompts/` |
| Carousels | `marketing/creative/carousels/` |
| PDF lead magnets | `marketing/lead-magnets/` |

## Remotion conventions

- Brand tokens at top of composition, no inline colours
- `useCurrentFrame`, `interpolate`, `spring` — never CSS transitions
- `premountFor={fps}` on every `<Sequence>`
- Timing as `seconds × fps`, never hardcoded frames
- Register in `Root.tsx` as both 1:1 (1080×1080) and 9:16 (1080×1920)
- Follow `remotion-best-practices` skill when loaded

## Higgsfield / AI video prompts

- Image-to-video (not text-to-video) — start with reference image path
- Gentle camera motion survives brand overlays
- Cinematic daylight, warm neutral grade
- 5s clips, 1080p+, 16:9 or 9:16
- Negative prompt always: `text, watermark, logo, subtitles, low quality, cartoon, oversaturated, neon`

## Brief requirements (reject if missing)

Asset type, dimensions, duration, use case, message, metric + review_date.

## POPIA/IP

- No real customer faces without signed consent
- AI imagery from licensed commercial tiers only
- Stock: Unsplash/Pexels CC0 with credit where required

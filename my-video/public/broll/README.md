# Higgsfield prompts for Klikk B-roll

Paste these directly into Higgsfield. Save each clip as an MP4 with the **exact filename** shown — Remotion picks them up automatically.

## Global settings (apply to every clip)

| Setting | Value |
|---|---|
| Duration | 5 seconds |
| Resolution | 1080p minimum (higher is fine) |
| Aspect | 16:9 (Remotion will crop for 1:1 and 9:16) |
| Frame rate | 30 fps |
| Style | Cinematic, natural daylight, warm neutral grade |
| Negative prompt | `text, watermark, logo, subtitles, low quality, distorted, cartoon, saturated colours, purple tint, neon` |

Keep colour grading muted — the Klikk navy (#2B2D6E) and pink (#FF3D7F) overlays sit on top, so oversaturated footage fights the brand.

---

## Clip 1 — `drone-suburb.mp4`

**Use:** Opening establishing shot (0–4s)

**Camera:** Drone, slow forward push
**Prompt:**
> Aerial drone shot slowly pushing forward over an upmarket South African residential suburb at golden hour. Tree-lined streets, whitewashed homes with terracotta roofs, blue swimming pools, distant mountains (Stellenbosch / Cape Winelands look). Warm amber sunlight, cinematic wide shot, shallow drifting motion, peaceful atmosphere.

---

## Clip 2 — `phone-scroll.mp4`

**Use:** "Viewing" moment (4–7s)

**Camera:** Static close-up, shallow depth of field
**Prompt:**
> Close-up of a young woman's hand scrolling through property listings on a modern smartphone. Clean white interface on the screen, soft natural window light, blurred cafe background in bokeh. Thumb swiping up slowly. Minimalist, modern, relatable. Shot on 50mm lens feel.

---

## Clip 3 — `signing-phone.mp4`

**Use:** "Lease execution" moment (7–10s)

**Camera:** Overhead top-down, static
**Prompt:**
> Overhead close-up of a finger signing a digital signature on a smartphone screen. The phone sits on a clean wooden desk. Soft directional shadow, warm daylight, shallow depth of field. A mug and notebook just visible at the edge of frame. Calm, professional, decisive gesture.

---

## Clip 4 — `empty-lounge.mp4`

**Use:** Closing "happy tenant" moment (25–30s, CTA scene)

**Camera:** First-person POV, slow walk forward
**Prompt:**
> First-person POV slowly walking into a sunlit empty lounge. Warm wooden floors, large windows pouring in soft daylight, a potted plant in the corner, white walls, minimalist modern South African home. Camera drifts forward gently. Optimistic, fresh-start feeling. No people visible.

---

## Optional extras (nice to have for longer cuts)

### `keys-handover.mp4`
> Close-up of two hands exchanging a set of house keys. Soft warm indoor light, shallow depth of field, clean wooden surface below. The keys catch the light. Shot on 85mm lens, cinematic.

### `viewing-couple.mp4`
> Cinematic medium shot of a young couple walking through an empty sunlit property, pointing at features, smiling. Natural daylight through large windows, warm tones, shallow depth of field. They look like a modern South African couple in their early 30s.

### `agent-handshake.mp4`
> Close-up handshake between a property agent and a new tenant in front of a modern home. Daylight, warm neutral grade, out-of-focus home in background. Professional, welcoming mood.

---

## Workflow

1. Generate each clip in Higgsfield (5s each, ~R40–80 per clip on paid tier)
2. Rename the download to match the filename above
3. Drop into this `public/broll/` folder
4. Open `src/LifecycleWithBroll.tsx` and flip `USE_BROLL = false` → `true`
5. Refresh Remotion Studio → `LifecycleWithBroll` now plays with real footage

## Licensing

Higgsfield paid tier allows commercial use of generated clips. Verify the specific model's terms before spending on Meta/Google ad placements.

## Tips

- **Generate 2–3 variants per clip**, pick the best. AI video models are lottery-ish.
- **Keep motion gentle** — fast or shaky AI motion reads as "AI" to viewers. Slow pushes, slow pans, static shots survive brand overlays best.
- **Avoid faces up close** unless the prompt explicitly gets the SA demographic right. Hands, objects, interiors, drone shots are safer.
- **Trim in Higgsfield first** if a clip has a weird first/last second. Remotion can also trim via `startFrom` / `endAt` on `<Video>`.

---
name: klikk-property-stellenbosch-intel
description: >
  Full 6-phase Winelands property intelligence pipeline. Collects from 8 portals, enriches
  with Google Street View, vectorizes, deduplicates, classifies via Claude Vision, exports
  to Google Maps. Use for property lookups, market scans, duplicate detection.
---

# Stellenbosch Property Intel

Full 6-phase intelligence pipeline for Winelands properties (Stellenbosch, Paarl, Franschhoek, Somerset West, Strand). Collects from 8 portals, enriches with Google Street View, vectorizes, deduplicates cross-site, classifies via Claude Vision, and exports to Google Maps.

## When to Use This Skill

- Looking up a specific property (e.g. "1 Bosch-en-Dal, Karindal")
- Running a market scan for Stellenbosch / Winelands
- Finding duplicate listings across portals
- Classifying properties by type, condition, architectural style
- Generating a Google Maps plot of available properties
- Triggers: "winelands intel", "market scan", "property map", "cross-site duplicates",
  "karindal", "bosch-en-dal", "classify properties"

---

## Areas & Sources

| Area slug | Display name |
|-----------|--------------|
| stellenbosch | Stellenbosch |
| paarl | Paarl |
| franschhoek | Franschhoek |
| somerset_west | Somerset West |
| strand | Strand |

Sources: property24, private_property, gumtree, iol_property, rentfind, pam_golding, seeff, facebook

---

## Reference Index

| Topic | File |
|-------|------|
| Phase 0 (single lookup), Phase 1 (full scrape), Phase 2 (image acquisition) | [phases-0-2.md](references/phases-0-2.md) |
| Phase 3 (vectorize), Phase 4 (deduplicate), Phase 5 (classify), Phase 6 (map export) | [phases-3-6.md](references/phases-3-6.md) |
| Full pipeline commands, market analysis queries, cost awareness, backend files | [analysis.md](references/analysis.md) |

---

## Quick Start

- **Single property lookup:** read [phases-0-2.md](references/phases-0-2.md) Phase 0
- **Full pipeline:** read [analysis.md](references/analysis.md) → Full Pipeline section
- **Market stats:** read [analysis.md](references/analysis.md) → Market Analysis Queries
- **Cost check before large run:** `classify_properties --dry-run --limit=N`

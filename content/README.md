# Klikk Content Hub

Single source of truth for product features, marketing copy, and sales materials.

## Structure

| Directory | Purpose |
|-----------|---------|
| `product/` | Feature registry, lifecycle, integrations, pricing |
| `brand/` | Voice, positioning, competitive intel |
| `sales/` | ICP, objections, demo flow, case studies |
| `website/copy/` | Page-level marketing copy |
| `changelog/` | Release notes linked to features.yaml |
| `cto/` | CTO-owned canonical references (legal citations, architecture-spanning decisions) — **read before publishing legal claims** |

## Website repository

The public site codebase lives in a **separate** Git repo (not this monorepo):

```text
git@github.com:michaelcdippenaar/klikk_property_manager_website.git
```

Clone it next to this project if you are working on the site:

```bash
git clone git@github.com:michaelcdippenaar/klikk_property_manager_website.git
```

Copy from `content/website/copy/` into that project (or wire a build step) as needed.

## Feature Status Values

| Status | Meaning | Website Badge |
|--------|---------|--------------|
| `BUILT` | Shipped and working | "Live" (green) |
| `IN_PROGRESS` | Currently being developed | "In Development" (amber) |
| `PLANNED` | On roadmap, not started | "Coming Soon" (gray) |
| `BETA` | Available but not GA | "Beta" (blue) |

## When You Ship a Feature

1. Open `product/features.yaml`
2. Change `status: BUILT` and set `shipped_date: YYYY-MM-DD`
3. Done. Website badges update at next build.

## When You Write Marketing Copy

1. Check `product/features.yaml` for current status
2. Never advertise PLANNED features as available
3. Follow `brand/voice.md` for tone and style
4. For any claim about SA legal compliance (POPIA, RHA, CPA, PIE), cite the section from `cto/rha-citation-canonical-map.md` — that is the only authoritative source for which section number to use. Skill .md files may lag. Run `python backend/manage.py verify_caselaw_citations` before committing copy that contains statute citations.

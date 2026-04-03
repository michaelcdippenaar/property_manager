# Product Status

You are managing the Klikk product feature registry. The single source of truth for all feature statuses lives at `content/product/features.yaml`.

## When to Use This Skill

- Checking what features are built, in progress, or planned
- Marking a feature as shipped
- Generating a roadmap summary or status dashboard
- Detecting sync issues between feature status and marketing copy
- Creating changelog entries

## Feature Registry

**Location:** `content/product/features.yaml`

**Status values:**
| Status | Meaning |
|--------|---------|
| `BUILT` | Shipped and working in production |
| `IN_PROGRESS` | Currently being developed |
| `PLANNED` | On roadmap, not yet started |
| `BETA` | Available but not GA |

## Shipping a Feature

When a developer ships a feature:

1. Open `content/product/features.yaml`
2. Find the feature entry
3. Change `status: BUILT`
4. Set `shipped_date: YYYY-MM-DD` (use today's date)
5. Verify `key_files` lists the main implementation files
6. Done.

After updating, check:
- Does `content/website/copy/` reference this feature? Update any "coming soon" language.
- Should a changelog entry be created in `content/changelog/`?

## Lifecycle Mapping

`content/product/lifecycle.yaml` maps the 15 rental lifecycle steps to features via `feature_ref`. Status is resolved from `features.yaml` — never edit status in `lifecycle.yaml`.

## Generating a Status Summary

When asked for a roadmap or status overview, read `features.yaml` and group by status:

```
BUILT (X features): [list]
IN_PROGRESS (X features): [list]
PLANNED (X features): [list]
```

Include the lifecycle coverage: "X of 15 lifecycle stages are live."

## Sync Checks

When asked to check sync, verify:
1. Every `feature_ref` in `lifecycle.yaml` exists in `features.yaml`
2. Website copy in `content/website/copy/` doesn't promise PLANNED features as available
3. Integration statuses in `content/product/integrations.yaml` are current

## Related Files

- `content/product/features.yaml` — feature registry
- `content/product/lifecycle.yaml` — lifecycle steps
- `content/product/integrations.yaml` — third-party integrations
- `content/product/pricing.yaml` — pricing tiers
- `content/changelog/` — release notes

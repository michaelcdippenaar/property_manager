/**
 * RNT-QUAL-047 — Feature-flag drift guard (Vitest / Node environment)
 *
 * Asserts set-equality between:
 *   - Every slug with `status: PLANNED` in content/product/features.yaml
 *   - The PLANNED_FEATURES Set in admin/src/composables/useFeatureFlags.ts
 *
 * Fails with a human-readable diff on any drift so engineers know exactly
 * which slugs are missing or extra.
 *
 * Run:
 *   cd admin && npx vitest run --config vitest.node.config.ts src/composables/__tests__/useFeatureFlags.drift.test.ts
 *
 * Or via npm script:
 *   cd admin && npm run test:drift
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// From admin/src/composables/__tests__/ go up 4 levels to reach repo root:
// __tests__ → composables → src → admin → repo-root
const __dirname = new URL('.', import.meta.url).pathname.replace(/\/$/, '')
const REPO_ROOT = resolve(__dirname, '..', '..', '..', '..')
const FEATURES_YAML = resolve(REPO_ROOT, 'content', 'product', 'features.yaml')
const FEATURE_FLAGS_TS = resolve(REPO_ROOT, 'admin', 'src', 'composables', 'useFeatureFlags.ts')

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Extract every slug with `status: PLANNED` from features.yaml.
 * Uses a simple line-scan so there's no external YAML dependency.
 */
function extractPlannedSlugsFromYaml(yamlText: string): Set<string> {
  const lines = yamlText.split('\n')
  const planned = new Set<string>()
  let lastSlug: string | null = null

  for (const line of lines) {
    const slugMatch = line.match(/^\s+slug:\s+(['"]?)([^'"#\s]+)\1/)
    if (slugMatch) {
      lastSlug = slugMatch[2]
      continue
    }
    const statusMatch = line.match(/^\s+status:\s+(['"]?)([A-Z_]+)\1/)
    if (statusMatch) {
      if (statusMatch[2] === 'PLANNED' && lastSlug) {
        planned.add(lastSlug)
      }
      lastSlug = null
    }
  }
  return planned
}

/**
 * Extract the quoted strings from the PLANNED_FEATURES Set literal in
 * useFeatureFlags.ts without importing the module (avoids Vue runtime deps).
 */
function extractPlannedSlugsFromTs(tsText: string): Set<string> {
  const setMatch = tsText.match(
    /const PLANNED_FEATURES\s*=\s*new Set<string>\(\[([\s\S]*?)\]\)/,
  )
  if (!setMatch) {
    throw new Error(
      'Could not find `const PLANNED_FEATURES = new Set<string>([...])` in useFeatureFlags.ts',
    )
  }
  const block = setMatch[1]
  const slugs = new Set<string>()
  const re = /['"]([^'"]+)['"]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(block)) !== null) {
    slugs.add(m[1])
  }
  return slugs
}

// ── Load files ────────────────────────────────────────────────────────────────

const yamlText = readFileSync(FEATURES_YAML, 'utf8')
const tsText = readFileSync(FEATURE_FLAGS_TS, 'utf8')

const yamlPlanned = extractPlannedSlugsFromYaml(yamlText)
const tsPlanned = extractPlannedSlugsFromTs(tsText)

const missingFromTs = [...yamlPlanned].filter((s) => !tsPlanned.has(s)).sort()
const extraInTs = [...tsPlanned].filter((s) => !yamlPlanned.has(s)).sort()

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Feature-flag drift guard', () => {
  it('PLANNED_FEATURES contains every slug marked PLANNED in features.yaml (no missing slugs)', () => {
    expect(
      missingFromTs,
      `Slugs with status PLANNED in features.yaml but MISSING from PLANNED_FEATURES:\n${missingFromTs.map((s) => `  + ${s}`).join('\n')}\n\nFix: add these slugs to PLANNED_FEATURES in admin/src/composables/useFeatureFlags.ts`,
    ).toEqual([])
  })

  it('PLANNED_FEATURES has no extra slugs absent from features.yaml (no phantom slugs)', () => {
    expect(
      extraInTs,
      `Slugs in PLANNED_FEATURES that have NO matching PLANNED entry in features.yaml:\n${extraInTs.map((s) => `  - ${s}`).join('\n')}\n\nFix: remove these slugs from PLANNED_FEATURES (or add them to features.yaml with status: PLANNED)`,
    ).toEqual([])
  })

  it('both sets are the same size (sanity check)', () => {
    expect(tsPlanned.size).toBe(yamlPlanned.size)
  })
})

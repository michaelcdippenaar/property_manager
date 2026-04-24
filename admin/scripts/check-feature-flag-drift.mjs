#!/usr/bin/env node
/**
 * RNT-QUAL-047 — Feature-flag drift guard
 *
 * Parses `content/product/features.yaml` to collect every slug with
 * `status: PLANNED`, then compares against the PLANNED_FEATURES Set in
 * `admin/src/composables/useFeatureFlags.ts`.
 *
 * Exits 1 with a human-readable diff if they diverge.
 * Exits 0 when in sync.
 *
 * Usage (from repo root):
 *   node admin/scripts/check-feature-flag-drift.mjs
 *
 * Usage (from admin/):
 *   node scripts/check-feature-flag-drift.mjs
 */

import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
// Resolve paths relative to repo root regardless of cwd
const REPO_ROOT = resolve(__dirname, '..', '..')
const FEATURES_YAML = resolve(REPO_ROOT, 'content', 'product', 'features.yaml')
const FEATURE_FLAGS_TS = resolve(REPO_ROOT, 'admin', 'src', 'composables', 'useFeatureFlags.ts')

// ── Parse features.yaml (no external YAML lib required) ──────────────────────
// We need every slug whose next/nearby line contains `status: PLANNED`.
// The YAML structure is:
//
//   some_key:
//     name: "..."
//     slug: some-slug
//     status: PLANNED
//
// Strategy: scan line-by-line, collect slug when the very next `status:` line
// after the slug line says PLANNED.

/**
 * Matches a two-space-indented feature-block key line in features.yaml
 * (e.g. `  some_feature_key:`). Used to detect a new feature block boundary
 * so `lastSlug` is reset when a block lacks a `slug:` or `status:` line,
 * preventing a stale slug from pairing with a later block's status.
 *
 * Kept in sync with the equivalent constant in
 * admin/src/composables/__tests__/useFeatureFlags.drift.test.ts.
 */
// eslint-disable-next-line no-useless-escape
const FEATURE_BLOCK_BOUNDARY_RE = /^  \w[\w-]*:/

function extractPlannedSlugsFromYaml(yamlText) {
  const lines = yamlText.split('\n')
  const planned = new Set()
  let lastSlug = null

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
      // Reset after we've seen the status for this feature block
      lastSlug = null
      continue
    }
    // Feature-block boundary: a new top-level feature key resets lastSlug so a
    // block that has a `slug:` but no `status:` cannot leak its slug into the
    // next block. Mirrors the reset in useFeatureFlags.drift.test.ts.
    if (FEATURE_BLOCK_BOUNDARY_RE.test(line)) {
      lastSlug = null
    }
  }

  return planned
}

// ── Parse useFeatureFlags.ts ──────────────────────────────────────────────────
// Extract the quoted strings inside `const PLANNED_FEATURES = new Set<string>([...])`.
function extractPlannedSlugsFromTs(tsText) {
  // Find the Set literal block
  const setMatch = tsText.match(/const PLANNED_FEATURES\s*=\s*new Set<string>\(\[([\s\S]*?)\]\)/)
  if (!setMatch) {
    throw new Error(
      'Could not find `const PLANNED_FEATURES = new Set<string>([...])` in useFeatureFlags.ts',
    )
  }
  const block = setMatch[1]
  const slugs = new Set()
  const re = /['"]([^'"]+)['"]/g
  let m
  while ((m = re.exec(block)) !== null) {
    slugs.add(m[1])
  }
  return slugs
}

// ── Main ──────────────────────────────────────────────────────────────────────
let yamlText, tsText
try {
  yamlText = readFileSync(FEATURES_YAML, 'utf8')
} catch (e) {
  console.error(`ERROR: Cannot read ${FEATURES_YAML}\n${e.message}`)
  process.exit(2)
}
try {
  tsText = readFileSync(FEATURE_FLAGS_TS, 'utf8')
} catch (e) {
  console.error(`ERROR: Cannot read ${FEATURE_FLAGS_TS}\n${e.message}`)
  process.exit(2)
}

const yamlPlanned = extractPlannedSlugsFromYaml(yamlText)
const tsPlanned = extractPlannedSlugsFromTs(tsText)

const missingFromTs = [...yamlPlanned].filter((s) => !tsPlanned.has(s)).sort()
const extraInTs = [...tsPlanned].filter((s) => !yamlPlanned.has(s)).sort()

if (missingFromTs.length === 0 && extraInTs.length === 0) {
  const count = yamlPlanned.size
  console.log(`OK — PLANNED_FEATURES is in sync with features.yaml (${count} slug${count !== 1 ? 's' : ''})`)
  process.exit(0)
}

console.error('DRIFT DETECTED — PLANNED_FEATURES in useFeatureFlags.ts does not match features.yaml\n')

if (missingFromTs.length > 0) {
  console.error('Slugs with status PLANNED in features.yaml but MISSING from PLANNED_FEATURES:')
  for (const s of missingFromTs) {
    console.error(`  + ${s}`)
  }
  console.error('')
}

if (extraInTs.length > 0) {
  console.error('Slugs in PLANNED_FEATURES that have NO matching PLANNED entry in features.yaml:')
  for (const s of extraInTs) {
    console.error(`  - ${s}`)
  }
  console.error('')
}

console.error('Fix: update PLANNED_FEATURES in admin/src/composables/useFeatureFlags.ts')
console.error('     to match the slugs marked `status: PLANNED` in content/product/features.yaml')
process.exit(1)

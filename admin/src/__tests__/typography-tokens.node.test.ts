/**
 * RNT-028 — Typography token guard (Vitest / Node environment)
 *
 * Locks in the typography scale set during the round-2 typography pass:
 *   - Tailwind `xl` → 22px (H1 anchor)
 *   - Tailwind `2xl` → 28px (stat values)
 *   - Body default in main.css → 16px
 *
 * If anyone shrinks these tokens again the test fails loudly so we don't
 * silently regress the WCAG / hierarchy work done in RNT-025 + RNT-028.
 *
 * Run:
 *   cd admin && npx vitest run --config vitest.node.config.ts \
 *     src/__tests__/typography-tokens.node.test.ts
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// __tests__ → src → admin
const __dirname = new URL('.', import.meta.url).pathname.replace(/\/$/, '')
const ADMIN_ROOT = resolve(__dirname, '..', '..')

describe('RNT-028 typography tokens', () => {
  it('Tailwind config exposes xl: 22px and 2xl: 28px', async () => {
    const mod = await import(resolve(ADMIN_ROOT, 'tailwind.config.js'))
    const fontSize = mod.default.theme.extend.fontSize

    expect(fontSize.xl?.[0]).toBe('22px')
    expect(fontSize['2xl']?.[0]).toBe('28px')
    // Sanity: small tier locked in from RNT-025
    expect(fontSize.sm?.[0]).toBe('15px')
    expect(fontSize.xs?.[0]).toBe('13px')
    expect(fontSize.micro?.[0]).toBe('12px')
    // Base + lg also pinned in RNT-028
    expect(fontSize.base?.[0]).toBe('16px')
    expect(fontSize.lg?.[0]).toBe('18px')
  })

  it('admin main.css body declares font-size: 16px', () => {
    const css = readFileSync(resolve(ADMIN_ROOT, 'src/assets/main.css'), 'utf8')
    // Match the body { ... font-size: 16px; ... } block.
    const bodyBlockMatch = css.match(/body\s*\{[^}]*\}/)
    expect(bodyBlockMatch).not.toBeNull()
    expect(bodyBlockMatch![0]).toMatch(/font-size:\s*16px/)
  })
})

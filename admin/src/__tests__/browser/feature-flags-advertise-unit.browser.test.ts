/**
 * UX-009 — Feature flag gate: "Advertise unit" hidden when PLANNED
 *
 * Verifies that:
 *   1. useFeatureFlags().isPlanned('vacancy-advertising') returns true
 *      (the slug is in the PLANNED set, matching features.yaml)
 *   2. A component that conditionally renders based on isPlanned() correctly
 *      hides the button when the feature is PLANNED
 *   3. A button for a BUILT feature slug (e.g. 'native-esigning') is NOT
 *      flagged as planned — ensuring isPlanned is selective
 *
 * Run:
 *   cd admin && npx vitest run src/__tests__/browser/feature-flags-advertise-unit.browser.test.ts
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useFeatureFlags } from '../../composables/useFeatureFlags'

// ---------------------------------------------------------------------------
// Helper — tiny wrapper component that renders a button conditionally.
// This mirrors what PropertyDetailView.vue does in the Actions dropdown.
// ---------------------------------------------------------------------------
function makeGatedButton(slug: string) {
  return defineComponent({
    name: 'GatedButton',
    setup() {
      const { isPlanned } = useFeatureFlags()
      return { isPlanned }
    },
    render() {
      return h(
        'div',
        {},
        !this.isPlanned(slug)
          ? [h('button', { class: 'menu-item', 'data-testid': 'action-btn' }, slug)]
          : [],
      )
    },
  })
}

// ---------------------------------------------------------------------------
// isPlanned() unit checks
// ---------------------------------------------------------------------------
describe('useFeatureFlags — isPlanned()', () => {
  it('returns true for vacancy-advertising (PLANNED in features.yaml)', () => {
    const { isPlanned } = useFeatureFlags()
    expect(isPlanned('vacancy-advertising')).toBe(true)
  })

  it('returns false for native-esigning (BUILT in features.yaml)', () => {
    const { isPlanned } = useFeatureFlags()
    expect(isPlanned('native-esigning')).toBe(false)
  })

  it('returns false for an unknown slug', () => {
    const { isPlanned } = useFeatureFlags()
    expect(isPlanned('some-nonexistent-feature')).toBe(false)
  })

  it('marks all rentals PLANNED slugs correctly', () => {
    const { isPlanned } = useFeatureFlags()
    const plannedSlugs = [
      'vacancy-advertising',
      'tenant-screening',
      'deposit-management',
      'incoming-inspection',
      'notice-management',
      'outgoing-inspection',
      'deposit-refund',
    ]
    for (const slug of plannedSlugs) {
      expect(isPlanned(slug), `Expected ${slug} to be PLANNED`).toBe(true)
    }
  })
})

// ---------------------------------------------------------------------------
// Component gate — button hidden when PLANNED
// ---------------------------------------------------------------------------
describe('GatedButton component — vacancy-advertising (PLANNED)', () => {
  it('does NOT render the button when feature is PLANNED', () => {
    const wrapper = mount(makeGatedButton('vacancy-advertising'))
    expect(wrapper.find('[data-testid="action-btn"]').exists()).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Component gate — button visible when NOT planned
// ---------------------------------------------------------------------------
describe('GatedButton component — native-esigning (BUILT)', () => {
  it('DOES render the button when feature is not PLANNED', () => {
    const wrapper = mount(makeGatedButton('native-esigning'))
    expect(wrapper.find('[data-testid="action-btn"]').exists()).toBe(true)
  })
})

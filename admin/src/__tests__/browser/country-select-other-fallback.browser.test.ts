/**
 * CountrySelect — "Other" with empty input must not emit a blank value
 * (regression test for Bug 5 / Round 2 reviewer report).
 *
 * Run:
 *   npx vitest run src/__tests__/browser/country-select-other-fallback.browser.test.ts
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CountrySelect from '../../components/CountrySelect.vue'

describe('CountrySelect — Other fallback', () => {
  it('does NOT emit a blank value when "Other" is selected with no text', async () => {
    const wrapper = mount(CountrySelect, {
      props: { modelValue: 'ZA' },
    })

    const select = wrapper.find('select').element as HTMLSelectElement
    select.value = '__OTHER__'
    await wrapper.find('select').trigger('change')

    // No update:modelValue should have fired with an empty value.
    const events = wrapper.emitted('update:modelValue') ?? []
    for (const args of events) {
      expect(args[0], 'must never emit blank fallback').not.toBe('')
    }
  })

  it('does NOT emit while user is typing a partial 1-letter code', async () => {
    const wrapper = mount(CountrySelect, {
      props: { modelValue: 'ZA' },
    })

    // Switch to Other so the input renders.
    const select = wrapper.find('select').element as HTMLSelectElement
    select.value = '__OTHER__'
    await wrapper.find('select').trigger('change')
    await wrapper.vm.$nextTick()

    const input = wrapper.find('input')
    expect(input.exists()).toBe(true)
    ;(input.element as HTMLInputElement).value = 'X'
    await input.trigger('input')

    const events = wrapper.emitted('update:modelValue') ?? []
    // After typing only 1 char we should still not have emitted a fresh value.
    expect(events.length).toBe(0)
  })

  it('emits the typed code only once 2 chars are entered', async () => {
    const wrapper = mount(CountrySelect, {
      props: { modelValue: 'ZA' },
    })

    const select = wrapper.find('select').element as HTMLSelectElement
    select.value = '__OTHER__'
    await wrapper.find('select').trigger('change')
    await wrapper.vm.$nextTick()

    const input = wrapper.find('input')
    ;(input.element as HTMLInputElement).value = 'XX'
    await input.trigger('input')

    const events = wrapper.emitted('update:modelValue') ?? []
    const last = events[events.length - 1]
    expect(last?.[0]).toBe('XX')
  })
})

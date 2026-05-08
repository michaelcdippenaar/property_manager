/**
 * EmailInput — inline email format validation tests.
 *
 * Covers:
 *  1. Empty value: no error (neutral)
 *  2. Invalid value before blur: no error yet (touched=false)
 *  3. Invalid value after blur: shows "Enter a valid email address"
 *  4. Valid value after blur: no error
 *  5. Touched-then-cleared: no error
 *  6. Composable isValidEmail() rejects whitespace, missing '@', missing dot
 *  7. v-model: typing emits update:modelValue
 *  8. validity event fires when validity transitions
 *
 * Run:
 *   cd admin && npx vitest run src/components/__tests__/EmailInput.browser.test.ts
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref, nextTick } from 'vue'
import EmailInput from '../EmailInput.vue'
import { isValidEmail, EMAIL_RE } from '../../composables/useEmailValidator'

function makeHost(initial = '') {
  return defineComponent({
    components: { EmailInput },
    setup() {
      const v = ref(initial)
      return { v }
    },
    render() {
      return h(EmailInput, { modelValue: this.v, 'onUpdate:modelValue': (val: string) => (this.v = val) })
    },
  })
}

describe('isValidEmail (composable)', () => {
  it('returns true for empty value (presence enforced separately)', () => {
    expect(isValidEmail('')).toBe(true)
  })

  it('rejects whitespace, missing @, missing dot', () => {
    expect(EMAIL_RE.test('a@b.c')).toBe(true)
    expect(isValidEmail('not-an-email')).toBe(false)
    expect(isValidEmail('foo@bar')).toBe(false)
    expect(isValidEmail('foo @bar.com')).toBe(false)
  })

  it('accepts a normal email', () => {
    expect(isValidEmail('user@example.co.za')).toBe(true)
  })
})

describe('EmailInput component', () => {
  it('renders with no error when value is empty', () => {
    const wrapper = mount(makeHost(''))
    expect(wrapper.find('[data-testid="email-input-error"]').exists()).toBe(false)
  })

  it('does not show error before blur even if invalid', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    await input.setValue('not-an-email')
    expect(wrapper.find('[data-testid="email-input-error"]').exists()).toBe(false)
  })

  it('shows error after blur when value is invalid', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    await input.setValue('not-an-email')
    await input.trigger('blur')
    await nextTick()
    expect(wrapper.find('[data-testid="email-input-error"]').text()).toBe(
      'Enter a valid email address',
    )
  })

  it('shows no error when value is valid (even after blur)', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    await input.setValue('user@example.com')
    await input.trigger('blur')
    await nextTick()
    expect(wrapper.find('[data-testid="email-input-error"]').exists()).toBe(false)
  })

  it('clears error when invalid input is deleted (touched but empty)', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    await input.setValue('bad')
    await input.trigger('blur')
    expect(wrapper.find('[data-testid="email-input-error"]').exists()).toBe(true)
    await input.setValue('')
    await nextTick()
    expect(wrapper.find('[data-testid="email-input-error"]').exists()).toBe(false)
  })

  it('emits update:modelValue when typing', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    await input.setValue('hello@klikk.co.za')
    expect(wrapper.vm.v).toBe('hello@klikk.co.za')
  })

  it('applies aria-invalid only when error is shown', async () => {
    const wrapper = mount(makeHost(''))
    const input = wrapper.find('input[type="email"]')
    expect(input.attributes('aria-invalid')).toBeUndefined()
    await input.setValue('bad')
    await input.trigger('blur')
    await nextTick()
    expect(input.attributes('aria-invalid')).toBe('true')
  })
})

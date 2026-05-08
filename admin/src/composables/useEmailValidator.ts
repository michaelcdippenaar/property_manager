/**
 * useEmailValidator — inline email validation composable.
 *
 * Provides reactive validity + error message for an email field.
 * Use alongside <input type="email"> or wrap with <EmailInput />.
 *
 *   const email = ref('')
 *   const { isValid, error, touched, markTouched } = useEmailValidator(email)
 *
 *   // In the template:
 *   <input v-model="email" type="email" @blur="markTouched()" :class="{ 'input-error': error }" />
 *   <p v-if="error" class="text-xs text-danger-600">{{ error }}</p>
 *
 * Validation rules:
 *  - Empty value is treated as valid (use HTML `required` to enforce presence).
 *  - The regex rejects whitespace, missing '@', and missing '.' in domain.
 */
import { computed, ref, type Ref } from 'vue'

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function isValidEmail(value: string | null | undefined): boolean {
  if (!value) return true
  return EMAIL_RE.test(value)
}

export function useEmailValidator(value: Ref<string>) {
  const touched = ref(false)

  const isValid = computed(() => isValidEmail(value.value))

  const error = computed(() => {
    if (!touched.value) return ''
    if (!value.value) return ''
    return EMAIL_RE.test(value.value) ? '' : 'Enter a valid email address'
  })

  function markTouched() {
    touched.value = true
  }

  function reset() {
    touched.value = false
  }

  return { isValid, error, touched, markTouched, reset }
}

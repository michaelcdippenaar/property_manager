<template>
  <!--
    EmailInput — drop-in replacement for <input type="email" class="input">
    that adds inline format validation as the user types.

    Behaviour:
      - Empty: neutral (no error, no error message)
      - Invalid (after blur): red border + "Enter a valid email address"
      - Valid: no message (we don't shout success)

    Usage:
      <EmailInput v-model="form.email" placeholder="email@example.com" />
      <EmailInput v-model="form.email" required />

    All other native <input> attributes (placeholder, autocomplete, id,
    aria-*, data-*) pass through via $attrs.
  -->
  <div>
    <input
      v-bind="$attrs"
      :value="modelValue"
      type="email"
      :class="[inputClass, error ? errorClass : '']"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      @input="onInput"
      @blur="onBlur"
    />
    <p
      v-if="error"
      :id="errorId"
      class="mt-1 text-xs text-danger-600"
      data-testid="email-input-error"
    >
      {{ error }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useEmailValidator } from '../composables/useEmailValidator'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    required?: boolean
    /** Tailwind class string applied to the <input>. Defaults to the project "input" class. */
    inputClass?: string
    /** Class added when the field is invalid (after blur). */
    errorClass?: string
  }>(),
  {
    modelValue: '',
    required: false,
    inputClass: 'input',
    errorClass: 'border-danger-500 focus:border-danger-500 focus:ring-danger-500',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'validity', valid: boolean): void
}>()

const internal = computed(() => String(props.modelValue ?? ''))
// useEmailValidator needs a writable Ref<string>-shaped reactive source;
// computed<string> satisfies the same interface for read-only access.
const { isValid, error, markTouched } = useEmailValidator(internal as unknown as import('vue').Ref<string>)

// Stable id for aria-describedby
let counter = 0
const errorId = `email-input-error-${++counter}-${Math.random().toString(36).slice(2, 7)}`

const lastValid = ref<boolean>(true)
function onInput(event: Event) {
  const v = (event.target as HTMLInputElement).value
  emit('update:modelValue', v)
  if (lastValid.value !== isValid.value) {
    lastValid.value = isValid.value
    emit('validity', isValid.value)
  }
}

function onBlur() {
  markTouched()
}

defineExpose({ isValid, error })
</script>

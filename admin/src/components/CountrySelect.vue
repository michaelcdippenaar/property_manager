<script setup lang="ts">
/**
 * Small country dropdown for Person forms (tenants, occupants, landlord reps).
 * Most-likely-12 list for SA-context users + "Other" trigger that swaps to free text.
 *
 * v-model: ISO 3166-1 alpha-2 code (e.g. "ZA", "GB", "NG").
 *
 * `compact` switches the option labels to "ZA — South Africa" style and
 * narrows the free-text fallback. `inputClass` lets the caller override
 * the default `input` styling so this matches sibling fields' font size.
 */
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string | null | undefined
  /** Optional id for label association */
  id?: string
  /** Optional aria-label / placeholder for the free-text fallback */
  ariaLabel?: string
  /** Compact mode for inline use beside narrow inputs */
  compact?: boolean
  /** Override the default `input` class on both select and free-text input */
  inputClass?: string
}>(), {
  compact: false,
  inputClass: '',
})
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const COMMON_COUNTRIES: { code: string; name: string }[] = [
  { code: 'ZA', name: 'South Africa' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'US', name: 'United States' },
  { code: 'ZW', name: 'Zimbabwe' },
  { code: 'NG', name: 'Nigeria' },
  { code: 'KE', name: 'Kenya' },
  { code: 'MZ', name: 'Mozambique' },
  { code: 'BW', name: 'Botswana' },
  { code: 'NA', name: 'Namibia' },
]

const KNOWN = new Set(COMMON_COUNTRIES.map(c => c.code))

const isOther = ref<boolean>(!!props.modelValue && !KNOWN.has(props.modelValue))
const otherText = ref<string>(isOther.value ? (props.modelValue || '') : '')

watch(() => props.modelValue, v => {
  if (v && !KNOWN.has(v)) {
    isOther.value = true
    otherText.value = v
  }
})

const selectValue = computed<string>(() => {
  if (isOther.value) return '__OTHER__'
  return props.modelValue || 'ZA'
})

const selectClass = computed(() => props.inputClass || 'input')
const otherInputBase = computed(() => props.inputClass || 'input')
const otherWidth = computed(() => props.compact ? 'w-14' : 'w-24')

function onSelect(e: Event) {
  const v = (e.target as HTMLSelectElement).value
  if (v === '__OTHER__') {
    isOther.value = true
    // Bug 5: don't emit a blank value when the user picks "Other" but
    // hasn't typed anything yet — that bypasses the Person model's ZA
    // default. Hold the existing value until they type a 2-letter code.
    if (otherText.value) emit('update:modelValue', otherText.value)
  } else {
    isOther.value = false
    emit('update:modelValue', v)
  }
}
function onOtherInput(e: Event) {
  otherText.value = (e.target as HTMLInputElement).value.toUpperCase().slice(0, 2)
  // Only emit when we have a complete 2-letter ISO code; otherwise the
  // previous value stays in place. Empty input never emits a blank.
  if (otherText.value.length === 2) {
    emit('update:modelValue', otherText.value)
  }
}
</script>

<template>
  <div class="flex gap-2 items-stretch">
    <select :id="id" :class="[selectClass, 'country-select']" :value="selectValue" @change="onSelect">
      <option v-for="c in COMMON_COUNTRIES" :key="c.code" :value="c.code">
        {{ compact ? `${c.code} — ${c.name}` : `${c.name} (${c.code})` }}
      </option>
      <option value="__OTHER__">Other (specify)</option>
    </select>
    <input
      v-if="isOther"
      :class="[otherInputBase, otherWidth, 'font-mono', 'uppercase']"
      maxlength="2"
      :placeholder="ariaLabel || 'ISO'"
      :value="otherText"
      @input="onOtherInput"
    />
  </div>
</template>

<style scoped>
.country-select { min-width: 4.5rem; }
</style>

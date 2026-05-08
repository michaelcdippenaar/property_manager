<script setup lang="ts">
/**
 * Small country dropdown for Person forms (tenants, occupants, landlord reps).
 * Most-likely-12 list for SA-context users + "Other" trigger that swaps to free text.
 *
 * v-model: ISO 3166-1 alpha-2 code (e.g. "ZA", "GB", "NG").
 */
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string | null | undefined
  /** Optional id for label association */
  id?: string
  /** Optional aria-label / placeholder for the free-text fallback */
  ariaLabel?: string
}>()
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

function onSelect(e: Event) {
  const v = (e.target as HTMLSelectElement).value
  if (v === '__OTHER__') {
    isOther.value = true
    emit('update:modelValue', otherText.value || '')
  } else {
    isOther.value = false
    emit('update:modelValue', v)
  }
}
function onOtherInput(e: Event) {
  otherText.value = (e.target as HTMLInputElement).value.toUpperCase().slice(0, 2)
  emit('update:modelValue', otherText.value)
}
</script>

<template>
  <div class="flex gap-2 items-stretch">
    <select :id="id" class="input" :value="selectValue" @change="onSelect">
      <option v-for="c in COMMON_COUNTRIES" :key="c.code" :value="c.code">
        {{ c.name }} ({{ c.code }})
      </option>
      <option value="__OTHER__">Other (specify)</option>
    </select>
    <input
      v-if="isOther"
      class="input w-24 font-mono uppercase"
      maxlength="2"
      :placeholder="ariaLabel || 'ISO'"
      :value="otherText"
      @input="onOtherInput"
    />
  </div>
</template>

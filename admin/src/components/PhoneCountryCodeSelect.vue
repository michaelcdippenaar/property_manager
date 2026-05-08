<script setup lang="ts">
/**
 * Small E.164 dialing-code dropdown. Defaults to +27 (South Africa).
 * v-model: dialing code with leading + (e.g. "+27", "+44").
 *
 * `compact` shrinks the visible label to just the dial code (no country
 * suffix) so the select fits beside narrow phone inputs in the
 * LeaseBuilder PersonBlock. `inputClass` lets the caller override the
 * default `input` styling (e.g. `'input text-xs py-1.5'`) so the select
 * matches sibling input font sizing.
 */
import { computed, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string | null | undefined
  id?: string
  compact?: boolean
  inputClass?: string
}>(), {
  compact: false,
  inputClass: '',
})
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const DIAL_CODES: { code: string; label: string }[] = [
  { code: '+27', label: '+27 (ZA)' },
  { code: '+44', label: '+44 (GB)' },
  { code: '+31', label: '+31 (NL)' },
  { code: '+49', label: '+49 (DE)' },
  { code: '+33', label: '+33 (FR)' },
  { code: '+1',  label: '+1 (US/CA)' },
  { code: '+263', label: '+263 (ZW)' },
  { code: '+234', label: '+234 (NG)' },
  { code: '+254', label: '+254 (KE)' },
  { code: '+258', label: '+258 (MZ)' },
  { code: '+267', label: '+267 (BW)' },
  { code: '+264', label: '+264 (NA)' },
]
const KNOWN = new Set(DIAL_CODES.map(d => d.code))

const isOther = ref<boolean>(!!props.modelValue && !KNOWN.has(props.modelValue))
const otherText = ref<string>(isOther.value ? (props.modelValue || '') : '')

watch(() => props.modelValue, v => {
  if (v && !KNOWN.has(v)) { isOther.value = true; otherText.value = v }
})

const selectValue = computed<string>(() => {
  if (isOther.value) return '__OTHER__'
  return props.modelValue || '+27'
})

const selectClass = computed(() => props.inputClass || 'input')
const otherInputBase = computed(() => props.inputClass || 'input')
const otherWidth = computed(() => props.compact ? 'w-14' : 'w-20')

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
  let raw = (e.target as HTMLInputElement).value.trim()
  if (raw && !raw.startsWith('+')) raw = '+' + raw
  otherText.value = raw.slice(0, 4)
  emit('update:modelValue', otherText.value)
}
</script>

<template>
  <div class="flex gap-2 items-stretch">
    <select
      :id="id"
      :class="[selectClass, 'phone-cc-select']"
      :value="selectValue"
      @change="onSelect"
    >
      <option v-for="d in DIAL_CODES" :key="d.code" :value="d.code">{{ compact ? d.code : d.label }}</option>
      <option value="__OTHER__">Other</option>
    </select>
    <input
      v-if="isOther"
      :class="[otherInputBase, otherWidth, 'font-mono']"
      maxlength="4"
      placeholder="+__"
      :value="otherText"
      @input="onOtherInput"
    />
  </div>
</template>

<style scoped>
.phone-cc-select { min-width: 4.5rem; }
</style>

<template>
  <input
    v-bind="$attrs"
    :value="modelValue"
    data-clarity-mask="true"
    autocomplete="off"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
/**
 * MaskedInput — drop-in replacement for <input> on PII fields.
 *
 * Automatically sets:
 *   - data-clarity-mask="true"  → prevents Microsoft Clarity from capturing the value
 *   - autocomplete="off"        → prevents browser from auto-filling PII into recordings
 *
 * Use wherever v-model binds to a PII field name listed in piiFields.ts:
 *   id_number, account_number, branch_code, trust_account_number,
 *   representative_id_number, passport
 *
 * Usage:
 *   <MaskedInput v-model="form.id_number" class="input font-mono" />
 *
 * Any extra attributes (class, type, placeholder, disabled, …) are forwarded
 * via $attrs (inheritAttrs: false is NOT set here — default pass-through applies).
 */
defineOptions({ inheritAttrs: false })

defineProps<{
  modelValue?: string | number | null
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

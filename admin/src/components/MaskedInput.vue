<template>
  <!--
    MaskedInput — a thin wrapper around <input> that automatically applies
    data-clarity-mask="true" and autocomplete="off" to prevent PII (SA ID,
    passport, bank account, branch code, trust account, passwords) from
    surfacing in Microsoft Clarity session replays.

    Usage:
      <MaskedInput v-model="form.id_number" class="input font-mono" placeholder="SA ID or passport" />
      <MaskedInput v-model="form.account_number" class="input" />

    All native <input> attributes pass through via v-bind="$attrs".
    The parent must still supply type, placeholder, class, etc. as needed.
    data-clarity-mask and autocomplete are applied here and cannot be overridden.

    PII field names that should always use this component:
      id_number, representative_id_number, passport, passport_number,
      account_number, branch_code, trust_account_number, trust_branch_code,
      current_password, new_password, password, pwConfirm
  -->
  <input
    v-bind="$attrs"
    :value="modelValue"
    data-clarity-mask="true"
    autocomplete="off"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
defineOptions({ inheritAttrs: false })

defineProps<{
  modelValue?: string | number | null
}>()

defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()
</script>

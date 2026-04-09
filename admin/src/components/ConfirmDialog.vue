<template>
  <BaseModal :open="open" :title="title" size="sm" @close="onCancel">
    <p class="text-sm text-gray-600 whitespace-pre-line">{{ description }}</p>

    <template #footer>
      <button class="btn-ghost" :disabled="loading" @click="onCancel">
        {{ cancelLabel }}
      </button>
      <button
        :class="variant === 'danger' ? 'btn-danger' : 'btn-primary'"
        :disabled="loading"
        @click="onConfirm"
      >
        {{ loading ? 'Working…' : confirmLabel }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import BaseModal from './BaseModal.vue'

withDefaults(defineProps<{
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'primary'
  loading?: boolean
}>(), {
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'danger',
  loading: false,
})

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function onConfirm() {
  emit('confirm')
}

function onCancel() {
  emit('cancel')
}
</script>

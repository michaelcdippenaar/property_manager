<template>
  <span class="badge" :class="cls">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: string; variant?: 'status' | 'priority' }>()

const STATUS_MAP: Record<string, { cls: string; label: string }> = {
  open:        { cls: 'badge-blue',   label: 'Open' },
  in_progress: { cls: 'badge-amber',  label: 'In Progress' },
  resolved:    { cls: 'badge-green',  label: 'Resolved' },
  closed:      { cls: 'badge-gray',   label: 'Closed' },
  pending:     { cls: 'badge-amber',  label: 'Pending' },
  completed:   { cls: 'badge-green',  label: 'Completed' },
  declined:    { cls: 'badge-red',    label: 'Declined' },
}

const PRIORITY_MAP: Record<string, { cls: string; label: string }> = {
  urgent: { cls: 'badge-red',    label: 'Urgent' },
  high:   { cls: 'badge-amber',  label: 'High' },
  medium: { cls: 'badge-blue',   label: 'Medium' },
  low:    { cls: 'badge-gray',   label: 'Low' },
}

const map = computed(() => props.variant === 'priority' ? PRIORITY_MAP : STATUS_MAP)
const cls   = computed(() => map.value[props.value]?.cls ?? 'badge-gray')
const label = computed(() => map.value[props.value]?.label ?? props.value)
</script>

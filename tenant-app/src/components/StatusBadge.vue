<template>
  <q-badge
    :color="badgeColor"
    :label="label"
    class="text-capitalize"
    rounded
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { maintenanceStatusColor, priorityColor, leaseStatusColor, signerStatusColor } from '../utils/formatters'

const props = withDefaults(defineProps<{
  value: string
  variant?: 'status' | 'priority' | 'lease' | 'signer'
}>(), {
  variant: 'status',
})

const label = computed(() => props.value.replace(/_/g, ' '))

const badgeColor = computed(() => {
  switch (props.variant) {
    case 'priority': return priorityColor(props.value)
    case 'lease':    return leaseStatusColor(props.value)
    case 'signer':   return signerStatusColor(props.value)
    default:         return maintenanceStatusColor(props.value)
  }
})
</script>

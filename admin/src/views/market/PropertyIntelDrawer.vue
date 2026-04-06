<template>
  <BaseDrawer :open="open" size="xl" @close="$emit('close')">
    <template #header>
      <div class="text-sm font-semibold text-gray-900">Property Intel</div>
    </template>
    <PropertyIntelPanel :listing-id="listingId" />
  </BaseDrawer>
</template>

<script setup lang="ts">
import BaseDrawer from '../../components/BaseDrawer.vue'
import PropertyIntelPanel from './PropertyIntelPanel.vue'

defineProps<{ open: boolean; listingId: number | null }>()
defineEmits<{ close: [] }>()
</script>

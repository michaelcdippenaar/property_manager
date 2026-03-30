<template>
  <BaseDrawer :open="open" size="xl" @close="$emit('close')">
    <template #header>
      <div>
        <div class="font-semibold text-gray-900 text-sm">{{ property?.name }}</div>
        <div class="text-xs text-gray-500">{{ property?.address }}</div>
      </div>
    </template>

    <div class="p-5 space-y-6">
      <!-- Property details -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Property</div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <div class="label">Property type</div>
            <div class="text-sm text-gray-900 capitalize">{{ property?.property_type }}</div>
          </div>
          <div>
            <div class="label">City</div>
            <div class="text-sm text-gray-900">{{ property?.city }}</div>
          </div>
          <div>
            <div class="label">Province</div>
            <div class="text-sm text-gray-900">{{ property?.province || '—' }}</div>
          </div>
          <div>
            <div class="label">Postal code</div>
            <div class="text-sm text-gray-900">{{ property?.postal_code || '—' }}</div>
          </div>
          <div class="col-span-2">
            <div class="label">Address</div>
            <div class="text-sm text-gray-900">{{ property?.address }}</div>
          </div>
        </div>
      </div>

      <!-- Units -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Units</div>
        <div v-if="!property?.units?.length" class="text-sm text-gray-400">No units yet.</div>
        <div v-for="u in property?.units" :key="u.id" class="card p-3 flex items-center justify-between">
          <div>
            <div class="text-sm font-medium text-gray-900">Unit {{ u.unit_number }}</div>
            <div class="text-xs text-gray-500">{{ u.bedrooms }} bed · {{ u.bathrooms }} bath</div>
          </div>
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full"
            :class="{
              'bg-emerald-50 text-emerald-700': u.status === 'occupied',
              'bg-blue-50 text-blue-700': u.status === 'available',
              'bg-amber-50 text-amber-700': u.status === 'maintenance',
            }"
          >
            {{ u.status }}
          </span>
        </div>
      </div>

      <div class="border-t border-gray-100" />

      <!-- Landlord / Ownership -->
      <LandlordTab v-if="property?.id" :property-id="property.id" />
    </div>
  </BaseDrawer>
</template>

<script setup lang="ts">
import BaseDrawer from '../../components/BaseDrawer.vue'
import LandlordTab from './LandlordTab.vue'

defineProps<{
  open: boolean
  property: any
}>()

defineEmits<{ close: [] }>()
</script>

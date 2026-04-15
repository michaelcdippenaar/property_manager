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
            class="text-xs font-medium"
            :class="{
              'badge-green': u.status === 'occupied',
              'badge-blue':  u.status === 'available',
              'badge-amber': u.status === 'maintenance',
              'badge-gray':  !['occupied','available','maintenance'].includes(u.status),
            }"
          >{{ u.status }}</span>
        </div>
      </div>

      <div class="border-t border-gray-100" />

      <!-- Landlord summary -->
      <div v-if="property?.id" class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Landlord</div>

        <div v-if="loadingOwner" class="flex items-center gap-2.5 animate-pulse" aria-label="Loading landlord">
          <div class="w-9 h-9 rounded-full bg-gray-200 flex-shrink-0" />
          <div class="flex-1 space-y-1.5">
            <div class="h-3 bg-gray-200 rounded w-1/3" />
            <div class="h-2.5 bg-gray-100 rounded w-1/2" />
          </div>
        </div>

        <div v-else-if="owner" class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0">
              <span class="text-navy font-semibold text-sm">{{ initials(owner.owner_name) }}</span>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-900">{{ owner.owner_name }}</div>
              <div class="text-xs text-gray-500">{{ owner.owner_email || owner.owner_phone || owner.owner_type }}</div>
            </div>
          </div>
          <RouterLink to="/landlords" class="text-xs text-navy hover:underline flex-shrink-0">
            Manage →
          </RouterLink>
        </div>

        <div v-else class="text-sm text-gray-400">
          No landlord set.
          <RouterLink to="/landlords" class="text-navy hover:underline ml-1">Set up →</RouterLink>
        </div>
      </div>

      <div class="border-t border-gray-100" />

      <!-- Linked lease template -->
      <div class="space-y-3">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Lease Template</div>

        <div v-if="loadingTemplate" class="flex items-center gap-2.5 animate-pulse" aria-label="Loading lease template">
          <div class="w-8 h-8 rounded-lg bg-gray-200 flex-shrink-0" />
          <div class="flex-1 space-y-1.5">
            <div class="h-3 bg-gray-200 rounded w-2/5" />
            <div class="h-2.5 bg-gray-100 rounded w-1/3" />
          </div>
        </div>

        <div v-else-if="linkedTemplate" class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-navy/10 flex items-center justify-center flex-shrink-0">
              <FileSignature :size="15" class="text-navy" />
            </div>
            <div>
              <div class="text-sm font-medium text-gray-900">{{ linkedTemplate.name }}</div>
              <div class="text-xs text-gray-500 capitalize">{{ linkedTemplate.template_type?.replace(/_/g, ' ') || 'Lease template' }}</div>
            </div>
          </div>
          <RouterLink
            :to="`/leases/templates/${linkedTemplate.id}/edit`"
            class="text-xs text-navy hover:underline flex-shrink-0"
          >
            Open →
          </RouterLink>
        </div>

        <div v-else class="flex items-center justify-between gap-3">
          <span class="text-sm text-gray-400">No template linked.</span>
          <RouterLink to="/leases/templates" class="text-xs text-navy hover:underline flex-shrink-0">
            Browse templates →
          </RouterLink>
        </div>
      </div>
    </div>
  </BaseDrawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseDrawer from '../../components/BaseDrawer.vue'
import { FileSignature } from 'lucide-vue-next'
import api from '../../api'
import { initials } from '../../utils/formatters'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import { useOwnershipsStore } from '../../stores/ownerships'

const toast = useToast()
const ownershipsStore = useOwnershipsStore()

const props = defineProps<{
  open: boolean
  property: any
}>()

defineEmits<{ close: [] }>()

const loadingOwner    = ref(false)
const loadingTemplate = ref(false)
const owner           = ref<any>(null)
const linkedTemplate  = ref<any>(null)

watch(() => props.property?.id, async (id) => {
  owner.value = null
  linkedTemplate.value = null
  if (!id) return

  // Load landlord / ownership summary (404 = no owner is normal)
  loadingOwner.value = true
  try {
    owner.value = await ownershipsStore.fetchCurrent(id)
  } catch (err: any) {
    toast.error(extractApiError(err, 'Failed to load landlord'))
  } finally { loadingOwner.value = false }

  // Load linked lease template
  loadingTemplate.value = true
  try {
    const { data } = await api.get('/leases/templates/', { params: { property: id, page_size: 1 } })
    const results = data.results ?? data
    linkedTemplate.value = results[0] ?? null
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to load lease template'))
  } finally { loadingTemplate.value = false }
}, { immediate: true })
</script>

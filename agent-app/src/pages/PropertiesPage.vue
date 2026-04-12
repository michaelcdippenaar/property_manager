<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadProperties">

      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else-if="properties.length === 0">
        <div class="empty-state">
          <q-icon name="home_work" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No properties assigned yet</div>
          <div class="empty-state-sub">Contact your admin to add properties to your account</div>
        </div>
      </template>

      <template v-else>
        <!-- Search -->
        <q-input
          v-model="search"
          placeholder="Search properties..."
          outlined
          :rounded="isIos"
          dense
          clearable
          class="q-mb-md"
        >
          <template #prepend>
            <q-icon name="search" color="grey-6" />
          </template>
        </q-input>

        <!-- Property cards -->
        <div class="column q-gutter-sm">
          <q-card
            v-for="prop in filteredProperties"
            :key="prop.id"
            flat
            class="property-card"
            clickable
            v-ripple
            @click="$router.push(`/properties/${prop.id}`)"
          >
            <!-- Cover photo -->
            <q-img
              v-if="prop.cover_photo"
              :src="prop.cover_photo"
              :alt="`Photo of ${prop.name}`"
              fit="cover"
              class="property-photo"
            />

            <div v-else class="property-placeholder row items-center justify-center">
              <q-icon name="home" size="48px" color="grey-4" />
            </div>

            <q-card-section class="q-pt-md q-pb-md">
              <div class="row items-start justify-between no-wrap">
                <div class="col">
                  <div class="text-subtitle1 text-weight-semibold text-primary ellipsis">{{ prop.name }}</div>
                  <div class="text-caption text-grey-6 ellipsis">{{ prop.address }}</div>
                </div>
                <q-icon name="chevron_right" color="grey-4" class="q-ml-sm" />
              </div>

              <!-- Summary badges -->
              <div class="row q-gutter-xs q-mt-sm">
                <q-badge outline color="primary" :label="`${prop.unit_count} unit${prop.unit_count !== 1 ? 's' : ''}`" />
                <q-badge
                  outline
                  color="positive"
                  :label="`${availableUnits(prop)} available`"
                />
                <q-badge
                  v-if="openIssueCount(prop) > 0"
                  color="negative"
                  :label="`${openIssueCount(prop)} open issue${openIssueCount(prop) !== 1 ? 's' : ''}`"
                  icon="build"
                />
                <q-badge
                  v-if="activityCount(prop) > 0"
                  color="warning"
                  text-color="dark"
                  :label="`${activityCount(prop)} message${activityCount(prop) !== 1 ? 's' : ''}`"
                  icon="chat_bubble"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </template>

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { listProperties, listMaintenanceRequests, type Property, type MaintenanceRequest } from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { SPINNER_SIZE_PAGE, EMPTY_ICON_SIZE } from '../utils/designTokens'

const $q = useQuasar()
const { isIos } = usePlatform()

const loading    = ref(true)
const properties = ref<Property[]>([])
const search     = ref('')
const openIssues = ref<MaintenanceRequest[]>([])

const filteredProperties = computed(() => {
  if (!search.value) return properties.value
  const q = search.value.toLowerCase()
  return properties.value.filter(
    (p) => p.name.toLowerCase().includes(q) || p.city.toLowerCase().includes(q),
  )
})

function availableUnits(prop: Property) {
  return prop.units?.filter((u) => u.status === 'available').length ?? 0
}

function propertyIssues(prop: Property): MaintenanceRequest[] {
  const unitIds = new Set(prop.units?.map((u) => u.id) ?? [])
  return openIssues.value.filter((r) => r.unit != null && unitIds.has(r.unit))
}

function openIssueCount(prop: Property): number {
  return propertyIssues(prop).length
}

function activityCount(prop: Property): number {
  return propertyIssues(prop).reduce((sum, r) => sum + (r.activity_count || 0), 0)
}

async function loadProperties(done?: () => void) {
  try {
    const [propsResp, issuesResp] = await Promise.allSettled([
      listProperties(),
      listMaintenanceRequests({ status: 'open' }),
    ])
    if (propsResp.status === 'fulfilled') properties.value = propsResp.value.results
    if (issuesResp.status === 'fulfilled') openIssues.value = issuesResp.value.results
    if (propsResp.status === 'rejected') {
      $q.notify({ type: 'negative', message: 'Failed to load properties. Pull down to retry.', icon: 'error' })
    }
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => void loadProperties())
</script>

<style scoped lang="scss">
.property-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  cursor: pointer;
}

.property-photo {
  display: block;
  width: 100%;
  height: 180px;
}

.property-placeholder {
  display: block;
  width: 100%;
  height: 120px;
  background: $surface;
}
</style>

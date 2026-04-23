<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadViewings">

      <!-- Loading -->
      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else>

        <!-- Search -->
        <q-input
          v-model="search"
          placeholder="Search prospect or property…"
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

        <!-- Status filter chips -->
        <div class="row q-gutter-xs q-mb-md">
          <q-chip
            v-for="s in statusFilters"
            :key="s.value"
            :selected="activeFilter === s.value"
            :color="activeFilter === s.value ? 'primary' : 'grey-2'"
            :text-color="activeFilter === s.value ? 'white' : 'grey-7'"
            clickable
            dense
            @click="activeFilter = s.value"
          >
            {{ s.label }}
          </q-chip>
        </div>

        <!-- Empty state -->
        <div v-if="filtered.length === 0" class="empty-state">
          <q-icon name="event_available" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No viewings found</div>
          <div v-if="activeFilter !== 'all'" class="empty-state-sub">
            Try changing the filter or search term
          </div>
          <q-btn
            v-else
            unelevated
            :rounded="isIos"
            color="secondary"
            label="Book a Viewing"
            icon="add"
            class="q-mt-md"
            @click="$router.push('/viewings/new')"
          />
        </div>

        <!-- Viewings list -->
        <div v-else class="column q-gutter-sm">
          <q-card
            v-for="v in filtered"
            :key="v.id"
            flat
            clickable
            v-ripple
            class="viewing-card"
            @click="$router.push(`/viewings/${v.id}`)"
          >
            <q-card-section class="q-pa-md">
              <!-- Header row -->
              <div class="row items-start justify-between q-mb-xs">
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold text-primary ellipsis">
                    {{ v.prospect_name }}
                  </div>
                  <div class="text-caption text-grey-6">
                    {{ v.property_name }}{{ v.unit_number ? ` · Unit ${v.unit_number}` : '' }}
                  </div>
                </div>
                <q-badge
                  :color="statusColor(v.status)"
                  :label="fmtLabel(v.status)"
                  class="q-ml-sm"
                />
              </div>

              <q-separator class="q-my-sm" />

              <!-- Details row -->
              <div class="row q-gutter-sm text-caption text-grey-7">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="event" size="14px" color="grey-5" />
                  <span>{{ formatDateTimeShort(v.scheduled_at) }}</span>
                </div>
                <div class="row items-center q-gutter-xs">
                  <q-icon name="timer" size="14px" color="grey-5" />
                  <span>{{ v.duration_minutes }}min</span>
                </div>
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
import { listViewings, type PropertyViewing } from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { statusColor, formatDateTimeShort, fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, EMPTY_ICON_SIZE } from '../utils/designTokens'

const $q = useQuasar()
const { isIos } = usePlatform()

const loading      = ref(true)
const viewings     = ref<PropertyViewing[]>([])
const search       = ref('')
const activeFilter = ref<string>('all')

const statusFilters = [
  { label: 'All',       value: 'all'       },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Confirmed', value: 'confirmed' },
  { label: 'Completed', value: 'completed' },
  { label: 'Converted', value: 'converted' },
  { label: 'Cancelled', value: 'cancelled' },
]

const filtered = computed(() => {
  let result = viewings.value

  if (activeFilter.value !== 'all') {
    result = result.filter((v) => v.status === activeFilter.value)
  }

  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    result = result.filter(
      (v) =>
        v.prospect_name.toLowerCase().includes(q) ||
        v.property_name.toLowerCase().includes(q),
    )
  }

  return result
})

async function loadViewings(done?: () => void) {
  try {
    const resp = await listViewings()
    viewings.value = resp.results
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load viewings. Pull down to retry.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => void loadViewings())
</script>

<style scoped lang="scss">
.viewing-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  cursor: pointer;
}
</style>

<template>
  <q-page class="q-pa-md">

    <!-- Pull to refresh -->
    <q-pull-to-refresh @refresh="loadData">

      <!-- Greeting -->
      <div class="q-mb-md">
        <div class="text-h6 text-weight-bold text-primary">
          Good {{ timeOfDay }}, {{ auth.user?.first_name || 'Agent' }}
        </div>
        <div class="text-caption text-grey-6">{{ todayStr }}</div>
      </div>

      <!-- Stats cards -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div class="col-4">
          <q-card flat class="stat-card text-center q-pa-md">
            <div class="text-h5 text-weight-bold text-primary">{{ stats.propertyCount }}</div>
            <div class="text-caption text-grey-6">Properties</div>
          </q-card>
        </div>
        <div class="col-4">
          <q-card flat class="stat-card text-center q-pa-md">
            <div class="text-h5 text-weight-bold text-secondary">{{ stats.viewingCount }}</div>
            <div class="text-caption text-grey-6">Viewings</div>
          </q-card>
        </div>
        <div class="col-4">
          <q-card flat class="stat-card text-center q-pa-md">
            <div class="text-h5 text-weight-bold text-positive">{{ availableCount }}</div>
            <div class="text-caption text-grey-6">Available</div>
          </q-card>
        </div>
      </div>

      <!-- Upcoming viewings -->
      <div class="text-subtitle2 text-weight-semibold text-grey-8 q-mb-sm">
        Upcoming Viewings
      </div>

      <div v-if="loading" class="row justify-center q-py-lg">
        <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
      </div>

      <template v-else-if="upcomingViewings.length === 0">
        <q-card flat class="empty-card text-center q-pa-xl">
          <q-icon name="event_available" :size="EMPTY_ICON_SIZE" color="grey-4" />
          <div class="text-body2 text-grey-5 q-mt-sm">No upcoming viewings</div>
          <q-btn
            outline
            color="primary"
            label="Book a Viewing"
            class="q-mt-md"
            :rounded="isIos"
            @click="$router.push('/viewings/new')"
          />
        </q-card>
      </template>

      <template v-else>
        <q-card flat class="section-card q-mb-md">
          <q-list separator>
            <q-item
              v-for="viewing in upcomingViewings.slice(0, 5)"
              :key="viewing.id"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${viewing.id}`)"
            >
              <q-item-section avatar>
                <q-avatar :color="statusColor(viewing.status)" text-color="white" :size="AVATAR_LIST">
                  <q-icon name="person" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">{{ viewing.prospect_name }}</q-item-label>
                <q-item-label caption>{{ viewing.property_name }}</q-item-label>
                <q-item-label caption class="text-grey-5">
                  <q-icon name="schedule" size="12px" />
                  {{ formatDateTimeShort(viewing.scheduled_at) }}
                </q-item-label>
              </q-item-section>

              <q-item-section side>
                <q-badge :color="statusColor(viewing.status)" :label="viewing.status" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <div v-if="upcomingViewings.length > 5" class="text-center">
          <q-btn flat color="primary" label="See all viewings" @click="$router.push('/calendar')" />
        </div>
      </template>

      <!-- iOS book viewing button -->
      <q-btn
        v-if="isIos"
        color="secondary"
        label="Book a Viewing"
        icon="add"
        class="full-width q-mt-md"
        rounded
        unelevated
        @click="$router.push('/viewings/new')"
      />

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'
import { getDashboardSummary, type PropertyViewing, type Property } from '../services/api'
import { statusColor, formatDateTimeShort } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, EMPTY_ICON_SIZE, AVATAR_LIST } from '../utils/designTokens'

const auth   = useAuthStore()
const { isIos } = usePlatform()

const loading         = ref(true)
const upcomingViewings = ref<PropertyViewing[]>([])
const properties       = ref<Property[]>([])
const stats            = ref({ propertyCount: 0, viewingCount: 0 })

const availableCount = computed(() =>
  properties.value.reduce((n, p) => n + p.units.filter((u) => u.status === 'available').length, 0),
)

const timeOfDay = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
})

const todayStr = computed(() =>
  new Date().toLocaleDateString('en-ZA', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)

async function loadData(done?: () => void) {
  try {
    const summary = await getDashboardSummary()
    upcomingViewings.value = summary.upcomingViewings
    properties.value       = summary.properties
    stats.value = {
      propertyCount: summary.propertyCount,
      viewingCount:  summary.viewingCount,
    }
  } catch {
    // Errors handled by axios interceptor (401 redirect etc.)
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => void loadData())
</script>

<style scoped lang="scss">
.stat-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: white;
}

.empty-card {
  border-radius: 12px;
  border: 1px dashed rgba(0, 0, 0, 0.12);
  background: transparent;
}
</style>

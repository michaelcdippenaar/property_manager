<template>
  <q-page v-if="property">

    <!-- ── Hero photo ──────────────────────────────────────────────────────── -->
    <q-img
      v-if="property.cover_photo"
      :src="property.cover_photo"
      :ratio="16/9"
      style="max-height:200px"
    >
      <div class="absolute-bottom property-photo-overlay">
        <div class="text-subtitle1 text-weight-bold">{{ property.name }}</div>
        <div class="text-caption text-white-7">
          <q-icon name="location_on" size="12px" />
          {{ property.address }}, {{ property.city }}
        </div>
      </div>
    </q-img>

    <!-- Property name header (no photo) -->
    <div v-else class="q-pa-md q-pb-xs">
      <div class="text-h6 text-weight-bold text-primary">{{ property.name }}</div>
      <div class="text-caption text-grey-6">
        <q-icon name="location_on" size="13px" />
        {{ property.address }}, {{ property.city }}, {{ property.province }}
      </div>
    </div>

    <!-- ── Tabs ────────────────────────────────────────────────────────────── -->
    <q-card flat class="tab-card q-mx-md q-mt-md">
      <q-tabs
        v-model="tab"
        dense
        align="justify"
        active-color="primary"
        indicator-color="secondary"
        class="text-grey-7"
        no-caps
      >
        <q-tab name="info"     label="Info" />
        <q-tab name="units"    label="Units" />
        <q-tab name="leases"   label="Leases" />
        <q-tab name="viewings" label="Viewings" />
      </q-tabs>
      <q-separator />

      <q-tab-panels v-model="tab" animated>

        <!-- ── INFO tab ──────────────────────────────────────────────────── -->
        <q-tab-panel name="info" class="q-pa-none">
          <q-list separator>

            <q-item>
              <q-item-section avatar>
                <q-icon name="home_work" color="grey-5" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>Property type</q-item-label>
                <q-item-label class="text-capitalize">{{ property.property_type || '—' }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="location_on" color="grey-5" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>Address</q-item-label>
                <q-item-label>{{ property.address }}</q-item-label>
                <q-item-label>{{ property.city }}, {{ property.province }} {{ property.postal_code }}</q-item-label>
              </q-item-section>
            </q-item>

            <q-item>
              <q-item-section avatar>
                <q-icon name="door_front" color="grey-5" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>Total units</q-item-label>
                <q-item-label>{{ property.unit_count }} unit{{ property.unit_count !== 1 ? 's' : '' }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge outline color="positive" :label="`${availableCount} available`" />
              </q-item-section>
            </q-item>

            <q-item v-if="property.description">
              <q-item-section avatar>
                <q-icon name="notes" color="grey-5" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>Description</q-item-label>
                <q-item-label class="text-body2" style="white-space: pre-wrap">{{ property.description }}</q-item-label>
              </q-item-section>
            </q-item>

          </q-list>
        </q-tab-panel>

        <!-- ── UNITS tab ──────────────────────────────────────────────────── -->
        <q-tab-panel name="units" class="q-pa-none">
          <q-list separator>
            <q-item
              v-for="unit in property.units"
              :key="unit.id"
              clickable
              v-ripple
              @click="bookViewing(unit.id)"
            >
              <q-item-section>
                <q-item-label class="text-weight-medium">Unit {{ unit.unit_number }}</q-item-label>
                <q-item-label caption>
                  {{ unit.bedrooms }}bd · {{ unit.bathrooms }}ba
                  <span v-if="unit.floor_size_m2"> · {{ unit.floor_size_m2 }}m²</span>
                </q-item-label>
                <q-item-label caption v-if="unit.active_lease_info?.tenant_name">
                  <q-icon name="person" size="12px" />
                  {{ unit.active_lease_info.tenant_name }}
                </q-item-label>
              </q-item-section>

              <q-item-section side top class="column items-end q-gutter-xs">
                <q-badge :color="unitStatusColor(unit.status)" :label="unit.status" class="text-capitalize" />
                <div class="text-caption text-weight-semibold text-primary">
                  R{{ Number(unit.rent_amount).toLocaleString('en-ZA') }}/mo
                </div>
                <q-icon v-if="unit.status === 'available'" name="chevron_right" color="grey-4" size="16px" />
              </q-item-section>
            </q-item>
          </q-list>

          <div class="q-pa-md" v-if="isIos">
            <q-btn unelevated rounded color="secondary" label="Book a Viewing" icon="add"
              class="full-width" @click="bookViewing()" />
          </div>
        </q-tab-panel>

        <!-- ── LEASES tab ─────────────────────────────────────────────────── -->
        <q-tab-panel name="leases" class="q-pa-none">
          <div v-if="loadingLeases" class="row justify-center q-py-lg">
            <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
          </div>

          <template v-else-if="propertyLeases.length === 0">
            <div class="text-center q-pa-xl">
              <q-icon name="description" :size="EMPTY_ICON_SIZE" color="grey-4" />
              <div class="text-body2 text-grey-5 q-mt-xs">No leases for this property</div>
              <q-btn
                unelevated
                :rounded="isIos"
                color="primary"
                label="Create Lease"
                icon="add"
                size="sm"
                class="q-mt-md"
                @click="$router.push(`/properties/${id}/leases/new`)"
              />
            </div>
          </template>

          <template v-else>
            <div class="q-pa-sm q-pb-xs row justify-end">
              <q-btn
                flat
                :rounded="isIos"
                color="primary"
                label="Create Lease"
                icon="add"
                size="sm"
                @click="$router.push(`/properties/${id}/leases/new`)"
              />
            </div>

          <q-list separator>
            <q-item v-for="lease in propertyLeases" :key="lease.id">
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ lease.unit_label }}</q-item-label>
                <q-item-label caption>
                  {{ lease.tenant_name || lease.all_tenant_names?.[0] || '—' }}
                </q-item-label>
                <q-item-label caption class="text-grey-5">
                  {{ formatDate(lease.start_date) }} – {{ formatDate(lease.end_date) }}
                </q-item-label>
              </q-item-section>

              <q-item-section side top class="column items-end q-gutter-xs">
                <q-badge :color="leaseStatusColor(lease.status)" :label="lease.status" class="text-capitalize" />
                <div class="text-caption text-weight-semibold text-positive">
                  R{{ Number(lease.monthly_rent).toLocaleString('en-ZA') }}/mo
                </div>
                <div v-if="daysRemaining(lease.end_date)" class="text-caption text-grey-5">
                  {{ daysRemaining(lease.end_date) }}d left
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          </template>
        </q-tab-panel>

        <!-- ── VIEWINGS tab ───────────────────────────────────────────────── -->
        <q-tab-panel name="viewings" class="q-pa-none">
          <div v-if="loadingViewings" class="row justify-center q-py-lg">
            <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
          </div>

          <template v-else-if="viewings.length === 0">
            <div class="text-center q-pa-xl">
              <q-icon name="calendar_today" :size="EMPTY_ICON_SIZE" color="grey-4" />
              <div class="text-body2 text-grey-5 q-mt-xs">No viewings booked</div>
              <q-btn flat color="secondary" label="Book viewing" size="sm"
                class="q-mt-sm" @click="bookViewing()" />
            </div>
          </template>

          <q-list v-else separator>
            <q-item
              v-for="v in viewings"
              :key="v.id"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${v.id}`)"
            >
              <q-item-section avatar>
                <q-avatar :color="statusColor(v.status)" text-color="white" :size="AVATAR_COMPACT">
                  <q-icon name="person" size="20px" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ v.prospect_name }}</q-item-label>
                <q-item-label caption>{{ formatDateTimeShort(v.scheduled_at) }}</q-item-label>
                <q-item-label v-if="v.unit_number" caption class="text-grey-5">Unit {{ v.unit_number }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="statusColor(v.status)" :label="v.status" />
              </q-item-section>
            </q-item>
          </q-list>

          <div class="q-pa-md" v-if="isIos && viewings.length > 0">
            <q-btn unelevated rounded color="secondary" label="Book Another" icon="add"
              class="full-width" @click="bookViewing()" />
          </div>
        </q-tab-panel>

      </q-tab-panels>
    </q-card>

    <div class="q-pb-xl" />

  </q-page>

  <q-page v-else-if="loading" class="row justify-center items-center">
    <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getProperty, listViewings, listLeases, type Property, type PropertyViewing, type AgentLease } from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { statusColor, unitStatusColor, leaseStatusColor, formatDate, formatDateTimeShort, daysRemaining } from '../utils/formatters'
import { SPINNER_SIZE_PAGE, SPINNER_SIZE_INLINE, EMPTY_ICON_SIZE, AVATAR_COMPACT } from '../utils/designTokens'

const props = defineProps<{ id: string }>()
const router = useRouter()
const { isIos } = usePlatform()

const tab             = ref('info')
const loading         = ref(true)
const loadingViewings = ref(false)
const loadingLeases   = ref(false)
const property        = ref<Property | null>(null)
const viewings        = ref<PropertyViewing[]>([])
const allLeases       = ref<AgentLease[]>([])

const availableCount = computed(() =>
  property.value?.units.filter((u) => u.status === 'available').length ?? 0,
)

const propertyLeases = computed(() =>
  allLeases.value.filter((l) => l.property_id === Number(props.id)),
)

function bookViewing(unitId?: number) {
  const query: Record<string, string> = { property: String(props.id) }
  if (unitId) query.unit = String(unitId)
  void router.push({ name: 'book-viewing', query })
}

// ── Data loading ─────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    property.value = await getProperty(Number(props.id))

    loadingViewings.value = true
    loadingLeases.value   = true

    const [viewingsResp, leasesResp] = await Promise.allSettled([
      listViewings({ property: Number(props.id) }),
      listLeases(),
    ])

    if (viewingsResp.status === 'fulfilled') viewings.value = viewingsResp.value.results
    if (leasesResp.status === 'fulfilled')   allLeases.value = leasesResp.value.results
  } finally {
    loading.value         = false
    loadingViewings.value = false
    loadingLeases.value   = false
  }
})
</script>

<style scoped lang="scss">
.tab-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-bottom: 16px;
}

.property-photo-overlay {
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.65));
  padding: 8px 12px 12px;
}
</style>

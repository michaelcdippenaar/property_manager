<template>
  <q-page class="q-pa-md" v-if="property">

    <!-- Property header -->
    <q-card flat class="q-mb-md section-card">
      <q-img
        v-if="property.cover_photo"
        :src="property.cover_photo"
        :ratio="16/9"
        class="property-hero"
      />
      <q-card-section>
        <div class="text-h6 text-weight-bold text-primary">{{ property.name }}</div>
        <div class="text-caption text-grey-6">
          <q-icon name="location_on" size="14px" />
          {{ property.address }}, {{ property.city }}, {{ property.province }}
        </div>
        <div class="row q-gutter-xs q-mt-sm">
          <q-badge outline color="grey-7" :label="property.property_type" />
          <q-badge outline color="primary" :label="`${property.unit_count} unit${property.unit_count !== 1 ? 's' : ''}`" />
        </div>
      </q-card-section>
    </q-card>

    <!-- Tabs -->
    <q-card flat class="section-card">
      <q-tabs
        v-model="tab"
        dense
        align="left"
        active-color="primary"
        indicator-color="secondary"
        class="text-grey-7"
      >
        <q-tab name="units"    label="Units" />
        <q-tab name="viewings" label="Viewings" />
      </q-tabs>
      <q-separator />

      <q-tab-panels v-model="tab" animated>

        <!-- ── Units tab ─────────────────────────────────────────────────── -->
        <q-tab-panel name="units" class="q-pa-none">
          <q-list separator>
            <q-item
              v-for="unit in property.units"
              :key="unit.id"
              clickable
              v-ripple
            >
              <q-item-section>
                <q-item-label class="text-weight-medium">Unit {{ unit.unit_number }}</q-item-label>
                <q-item-label caption>
                  {{ unit.bedrooms }}bd · {{ unit.bathrooms }}ba
                  <span v-if="unit.floor_size_m2"> · {{ unit.floor_size_m2 }}m²</span>
                </q-item-label>
                <q-item-label caption v-if="unit.active_lease_info">
                  <q-icon name="person" size="12px" />
                  {{ unit.active_lease_info.tenant_name }}
                </q-item-label>
              </q-item-section>

              <q-item-section side top class="column items-end q-gutter-xs">
                <q-badge
                  :color="unitStatusColor(unit.status)"
                  :label="unit.status"
                  class="text-capitalize"
                />
                <div class="text-caption text-weight-semibold text-primary">
                  R{{ Number(unit.rent_amount).toLocaleString('en-ZA') }}
                </div>
              </q-item-section>
            </q-item>
          </q-list>

          <!-- Book viewing CTA (iOS style inline button) -->
          <div class="q-pa-md" v-if="isIos">
            <q-btn
              unelevated
              rounded
              color="secondary"
              label="Book a Viewing"
              icon="add"
              class="full-width"
              @click="bookViewing()"
            />
          </div>
        </q-tab-panel>

        <!-- ── Viewings tab ───────────────────────────────────────────────── -->
        <q-tab-panel name="viewings" class="q-pa-none">
          <div v-if="loadingViewings" class="row justify-center q-py-lg">
            <q-spinner-dots color="primary" size="28px" />
          </div>

          <template v-else-if="viewings.length === 0">
            <div class="text-center q-pa-xl">
              <q-icon name="calendar_today" size="40px" color="grey-4" />
              <div class="text-body2 text-grey-5 q-mt-xs">No viewings booked</div>
              <q-btn
                flat
                color="secondary"
                label="Book viewing"
                size="sm"
                class="q-mt-sm"
                @click="bookViewing()"
              />
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
                <q-avatar :color="statusColor(v.status)" text-color="white" size="36px">
                  <q-icon name="person" size="20px" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ v.prospect_name }}</q-item-label>
                <q-item-label caption>{{ formatDateTime(v.scheduled_at) }}</q-item-label>
                <q-item-label v-if="v.unit_number" caption class="text-grey-5">Unit {{ v.unit_number }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="statusColor(v.status)" :label="v.status" />
              </q-item-section>
            </q-item>
          </q-list>

          <div class="q-pa-md" v-if="isIos && viewings.length > 0">
            <q-btn unelevated rounded color="secondary" label="Book Another" icon="add" class="full-width" @click="bookViewing()" />
          </div>
        </q-tab-panel>

      </q-tab-panels>
    </q-card>

  </q-page>

  <q-page v-else-if="loading" class="row justify-center items-center">
    <q-spinner-dots color="primary" size="40px" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getProperty, listViewings, type Property, type PropertyViewing } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const props = defineProps<{ id: string }>()
const router = useRouter()
const { isIos } = usePlatform()

const tab            = ref('units')
const loading        = ref(true)
const loadingViewings = ref(false)
const property       = ref<Property | null>(null)
const viewings       = ref<PropertyViewing[]>([])

function unitStatusColor(status: string) {
  return status === 'available' ? 'positive' : status === 'occupied' ? 'negative' : 'warning'
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    scheduled: 'info', confirmed: 'primary', completed: 'positive',
    cancelled: 'negative', converted: 'secondary',
  }
  return map[status] || 'grey'
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function bookViewing(unitId?: number) {
  const query: Record<string, string> = { property: String(props.id) }
  if (unitId) query.unit = String(unitId)
  void router.push({ name: 'book-viewing', query })
}

onMounted(async () => {
  try {
    property.value = await getProperty(Number(props.id))
    loadingViewings.value = true
    const resp = await listViewings({ property: Number(props.id) })
    viewings.value = resp.results
  } finally {
    loading.value = false
    loadingViewings.value = false
  }
})
</script>

<style scoped lang="scss">
.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.08);
  overflow: hidden;
}

.property-hero {
  max-height: 200px;
}
</style>

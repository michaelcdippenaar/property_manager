<template>
  <q-page class="pipeline-page">

    <!-- ── Funnel header ── -->
    <div class="funnel-bar">
      <button
        v-for="stage in stages"
        :key="stage.id"
        class="funnel-stage"
        :class="{ 'funnel-stage--active': activeStage === stage.id }"
        @click="activeStage = stage.id"
      >
        <span class="funnel-stage-count">{{ stage.count }}</span>
        <span class="funnel-stage-label">{{ stage.label }}</span>
      </button>
    </div>

    <!-- ── Forecast ribbon ── -->
    <div class="forecast-ribbon">
      <q-icon name="trending_up" size="16px" :color="isIos ? 'primary' : 'white'" />
      <span class="forecast-text">
        Forecast commission this month
      </span>
      <span class="forecast-value">R 184,000</span>
    </div>

    <!-- ── Stage content ── -->
    <div class="stage-body">
      <div class="stage-heading">
        <h2 class="stage-title">{{ activeStageLabel }}</h2>
        <q-btn
          flat
          dense
          no-caps
          size="sm"
          color="primary"
          label="Filter"
          icon-right="tune"
        />
      </div>

      <q-pull-to-refresh @refresh="loadData">

        <!-- Mandates -->
        <template v-if="activeStage === 'mandates'">
          <div class="stack">
            <q-card flat v-for="item in mandates" :key="item.id" class="stack-card">
              <div class="stack-card-header">
                <div class="stack-card-title">{{ item.address }}</div>
                <q-badge :color="item.stageColor" :label="item.stage" />
              </div>
              <div class="stack-card-body">
                <div class="meta-row">
                  <q-icon name="person_outline" size="14px" color="grey-6" />
                  <span>{{ item.landlord }}</span>
                </div>
                <div class="meta-row">
                  <q-icon name="payments" size="14px" color="grey-6" />
                  <span>{{ item.monthlyRent }} · est. commission {{ item.commission }}</span>
                </div>
              </div>
              <div class="stack-card-foot">
                <q-btn flat dense no-caps size="sm" color="primary" label="Open" />
                <q-space />
                <span class="foot-note">{{ item.daysInStage }}d in stage</span>
              </div>
            </q-card>
          </div>
        </template>

        <!-- Listings -->
        <template v-else-if="activeStage === 'listings'">
          <div class="stack">
            <q-card flat v-for="item in listings" :key="item.id" class="stack-card">
              <div class="stack-card-header">
                <div class="stack-card-title">{{ item.address }}</div>
                <q-badge
                  :color="item.daysOnMarket > 21 ? 'warning' : item.daysOnMarket > 45 ? 'negative' : 'primary'"
                  :label="`${item.daysOnMarket}d on market`"
                />
              </div>
              <div class="stack-card-body">
                <div class="meta-row">
                  <q-icon name="visibility" size="14px" color="grey-6" />
                  <span>{{ item.views }} views · {{ item.enquiries }} enquiries</span>
                </div>
                <div class="meta-row">
                  <q-icon name="event" size="14px" color="grey-6" />
                  <span>{{ item.viewingsBooked }} viewings booked</span>
                </div>
              </div>
              <div class="portal-row">
                <span v-for="p in item.portals" :key="p" class="portal-chip">{{ p }}</span>
              </div>
            </q-card>
          </div>
        </template>

        <!-- Viewings -->
        <template v-else-if="activeStage === 'viewings'">
          <div class="stack">
            <q-card
              flat
              v-for="v in viewingsList"
              :key="v.id"
              class="stack-card"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${v.id}`)"
            >
              <div class="stack-card-header">
                <div class="stack-card-title">{{ v.prospect_name }}</div>
                <q-badge :color="statusColor(v.status)" :label="fmtLabel(v.status)" />
              </div>
              <div class="stack-card-body">
                <div class="meta-row">
                  <q-icon name="home_outlined" size="14px" color="grey-6" />
                  <span>{{ v.property_name }}</span>
                </div>
                <div class="meta-row">
                  <q-icon name="schedule" size="14px" color="grey-6" />
                  <span>{{ formatDateTimeShort(v.scheduled_at) }}</span>
                </div>
              </div>
            </q-card>

            <div v-if="viewingsList.length === 0 && !loading" class="empty-state">
              <q-icon name="event_available" size="40px" color="grey-4" />
              <div class="empty-state-title">No viewings in pipeline</div>
              <div class="empty-state-sub">Book one to get started</div>
            </div>
          </div>
        </template>

        <!-- Applications -->
        <template v-else-if="activeStage === 'applications'">
          <div class="stack">
            <q-card flat v-for="app in applications" :key="app.id" class="stack-card">
              <div class="stack-card-header">
                <div class="stack-card-title">{{ app.prospectName }}</div>
                <div class="score-pill" :class="`score-pill--${app.tier}`">{{ app.score }}</div>
              </div>
              <div class="stack-card-body">
                <div class="meta-row">
                  <q-icon name="home_outlined" size="14px" color="grey-6" />
                  <span>{{ app.property }}</span>
                </div>
                <div class="meta-row">
                  <q-icon name="payments" size="14px" color="grey-6" />
                  <span>Income / rent: <strong>{{ app.incomeRatio }}×</strong> · Credit: {{ app.credit }}</span>
                </div>
              </div>
              <div class="stack-card-foot">
                <q-btn flat dense no-caps size="sm" color="primary" label="Review" />
                <q-space />
                <q-btn flat dense no-caps size="sm" color="positive" icon="check" label="Approve" />
              </div>
            </q-card>
          </div>
        </template>

        <div v-if="loading" class="row justify-center q-py-xl">
          <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
        </div>

      </q-pull-to-refresh>

      <div class="tab-bar-spacer" />
    </div>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useQuasar } from 'quasar'
import { usePlatform } from '../composables/usePlatform'
import { listViewings, type PropertyViewing } from '../services/api'
import { statusColor, formatDateTimeShort, fmtLabel } from '../utils/formatters'
import { SPINNER_SIZE_PAGE } from '../utils/designTokens'

const $q = useQuasar()
const { isIos } = usePlatform()
const setPageTitle = inject<(t: string | null) => void>('setPageTitle')

type StageId = 'mandates' | 'listings' | 'viewings' | 'applications'
const activeStage = ref<StageId>('listings')

const viewingsList = ref<PropertyViewing[]>([])
const loading = ref(true)

// Backend endpoints for mandates/listings/applications roll up later — stubbed for now
const mandates = ref([
  { id: 1, address: 'Erf 217, De Klerk Ave',    landlord: 'G. Van Wyk',   monthlyRent: 'R 22,500', commission: 'R 20,250', stage: 'Pitching',   stageColor: 'info',    daysInStage: 4 },
  { id: 2, address: '7 Weidelands Cres',        landlord: 'AirCent Pty',  monthlyRent: 'R 18,000', commission: 'R 16,200', stage: 'Docs out',   stageColor: 'primary', daysInStage: 2 },
  { id: 3, address: '14 Bosch Street Villa',    landlord: 'M. Adams',     monthlyRent: 'R 35,000', commission: 'R 31,500', stage: 'Researching', stageColor: 'grey-7', daysInStage: 9 },
])

const listings = ref([
  { id: 1, address: '14 Bosch St',           daysOnMarket: 2,  views: 412, enquiries: 18, viewingsBooked: 6, portals: ['P24', 'PP', 'IG', 'WA'] },
  { id: 2, address: '22 De Klerk Ave',       daysOnMarket: 12, views: 271, enquiries: 9,  viewingsBooked: 3, portals: ['P24', 'PP'] },
  { id: 3, address: '7A Ryneveld Garden',    daysOnMarket: 28, views: 134, enquiries: 4,  viewingsBooked: 1, portals: ['P24'] },
])

const applications = ref([
  { id: 1, prospectName: 'John Dlamini',   property: '14 Bosch St',     score: 94, tier: 'top',    incomeRatio: 3.8, credit: 712 },
  { id: 2, prospectName: 'Nomvula Zulu',   property: '22 De Klerk Ave', score: 88, tier: 'strong', incomeRatio: 3.2, credit: 685 },
  { id: 3, prospectName: 'Andrew Meyer',   property: '14 Bosch St',     score: 72, tier: 'fair',   incomeRatio: 3.0, credit: 620 },
])

const stages = computed(() => ([
  { id: 'mandates' as StageId,    label: 'Mandates',    count: mandates.value.length },
  { id: 'listings' as StageId,    label: 'Listings',    count: listings.value.length },
  { id: 'viewings' as StageId,    label: 'Viewings',    count: viewingsList.value.length },
  { id: 'applications' as StageId, label: 'Apps',        count: applications.value.length },
]))

const activeStageLabel = computed(() =>
  stages.value.find((s) => s.id === activeStage.value)?.label ?? '',
)

async function loadData(done?: () => void) {
  try {
    const res = await listViewings({ status: 'scheduled,confirmed,completed' })
    viewingsList.value = res.results ?? []
  } catch {
    $q.notify({ type: 'negative', message: 'Pipeline load failed.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => {
  setPageTitle?.('Pipeline')
  void loadData()
})
</script>

<style scoped lang="scss">
.pipeline-page {
  background: var(--klikk-surface);
  padding: 8px 0 0;
  min-height: 100vh;
}

/* ── Funnel header ── */
.funnel-bar {
  display: flex;
  gap: 8px;
  padding: 12px 16px 8px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.funnel-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 14px;
  min-width: 72px;
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: var(--klikk-shadow-soft);

  &--active {
    background: $primary;
    border-color: $primary;

    .funnel-stage-count,
    .funnel-stage-label {
      color: white;
    }
  }

  &:active:not(&--active) {
    opacity: 0.7;
  }
}

.funnel-stage-count {
  font-size: 20px;
  font-weight: 800;
  color: $primary;
  line-height: 1;
  letter-spacing: -0.02em;
}

.funnel-stage-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

/* ── Forecast ribbon ── */
.forecast-ribbon {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 16px 16px;
  padding: 10px 14px;
  background: rgba(43, 45, 110, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(43, 45, 110, 0.12);
}

.forecast-text {
  font-size: 12px;
  color: var(--klikk-text-secondary);
  font-weight: 500;
}

.forecast-value {
  margin-left: auto;
  font-size: 14px;
  font-weight: 800;
  color: $primary;
  letter-spacing: -0.01em;
}

/* ── Stage body ── */
.stage-body {
  padding: 0 16px;
}

.stage-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.stage-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--klikk-text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stack-card {
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  box-shadow: var(--klikk-shadow-soft);
  overflow: hidden;
}

.stack-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 8px;
}

.stack-card-title {
  flex: 1;
  font-size: 15px;
  font-weight: 700;
  color: var(--klikk-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.3;
}

.stack-card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 14px 10px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--klikk-text-secondary);

  strong {
    color: var(--klikk-text-primary);
    font-weight: 700;
  }
}

.stack-card-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px 8px;
  border-top: 1px solid var(--klikk-border);
}

.foot-note {
  font-size: 11px;
  color: var(--klikk-text-muted);
  padding-right: 8px;
}

.portal-row {
  display: flex;
  gap: 6px;
  padding: 0 14px 12px;
  flex-wrap: wrap;
}

.portal-chip {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: $primary;
  background: rgba(43, 45, 110, 0.08);
  padding: 3px 8px;
  border-radius: 6px;
}

/* Applicant score pill */
.score-pill {
  font-size: 13px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  letter-spacing: -0.01em;

  &--top    { background: rgba(20, 184, 166, 0.12); color: $positive; }
  &--strong { background: rgba(43, 45, 110, 0.12);  color: $primary;  }
  &--fair   { background: rgba(245, 158, 11, 0.12); color: $warning;  }
  &--weak   { background: rgba(220, 38, 38, 0.10);  color: $negative; }
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 40px 24px;
  text-align: center;
}

.empty-state-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--klikk-text-primary);
  margin-top: 4px;
}

.empty-state-sub {
  font-size: 13px;
  color: var(--klikk-text-secondary);
}

.tab-bar-spacer {
  height: calc(90px + env(safe-area-inset-bottom, 0px));
}
</style>

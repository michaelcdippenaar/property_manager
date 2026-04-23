<template>
  <q-page class="today-page">
    <q-pull-to-refresh @refresh="loadData">

      <!-- ── Earnings hero ── -->
      <div class="earnings-hero">
        <div class="earnings-label">Commission this month</div>
        <div class="earnings-value">{{ formatZAR(earnings.earned) }}</div>
        <div class="earnings-meta">
          <span class="earnings-pct">{{ earnings.targetPct }}%</span>
          <span class="earnings-target">of {{ formatZAR(earnings.target) }} target</span>
        </div>
        <div class="earnings-track">
          <div class="earnings-fill" :style="{ width: `${Math.min(earnings.targetPct, 100)}%` }" />
        </div>
      </div>

      <!-- ── Next move ── -->
      <div class="next-move-wrap">
        <div class="next-move-eyebrow">Your next move</div>

        <q-card flat class="next-move-card" v-if="!loading && nextMove">
          <div class="next-move-body">
            <div class="next-move-title">{{ nextMove.title }}</div>
            <div class="next-move-sub">{{ nextMove.subtitle }}</div>

            <div class="next-move-impact">
              <q-icon name="trending_up" size="16px" />
              <span>Impact: <strong>{{ formatZAR(nextMove.impact) }}</strong></span>
            </div>
          </div>

          <q-btn
            color="primary"
            class="next-move-cta"
            :rounded="isIos"
            unelevated
            :label="nextMove.cta"
            :icon-right="isIos ? 'chevron_right' : 'arrow_forward'"
            @click="handleNextMove"
          />
        </q-card>

        <div v-else-if="loading" class="next-move-skeleton">
          <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
        </div>
      </div>

      <!-- ── Later (collapsible sections) ── -->
      <div class="later-section">
        <div class="later-header">Later today</div>

        <!-- Today's viewings -->
        <q-card flat class="later-card" v-if="upcomingViewings.length > 0">
          <div class="later-card-header">
            <q-icon name="event" size="16px" color="primary" />
            <span>{{ upcomingViewings.length }} viewing{{ upcomingViewings.length === 1 ? '' : 's' }} today</span>
          </div>

          <q-list separator>
            <q-item
              v-for="viewing in upcomingViewings.slice(0, 3)"
              :key="viewing.id"
              clickable
              v-ripple
              @click="$router.push(`/viewings/${viewing.id}`)"
            >
              <q-item-section avatar>
                <div class="viewing-time">
                  <div class="viewing-time-hour">{{ formatHour(viewing.scheduled_at) }}</div>
                  <div class="viewing-time-meridiem">{{ formatMeridiem(viewing.scheduled_at) }}</div>
                </div>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ viewing.prospect_name }}</q-item-label>
                <q-item-label caption>{{ viewing.property_name }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon :name="isIos ? 'chevron_right' : 'chevron_right'" color="grey-5" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <q-card flat class="later-card later-card-empty" v-else-if="!loading">
          <q-icon name="event_available" size="20px" color="grey-5" />
          <span>No viewings today</span>
        </q-card>

        <!-- Pipeline pulse -->
        <q-card flat class="later-card">
          <div class="later-card-header">
            <q-icon name="insights" size="16px" color="primary" />
            <span>Pipeline pulse</span>
            <q-space />
            <q-btn flat dense no-caps size="sm" label="Open" color="primary" @click="$router.push('/pipeline')" />
          </div>

          <div class="pulse-grid">
            <div class="pulse-item">
              <div class="pulse-value">{{ pipeline.mandates }}</div>
              <div class="pulse-label">Active mandates</div>
            </div>
            <div class="pulse-item pulse-item--warn" v-if="pipeline.stale > 0">
              <div class="pulse-value">{{ pipeline.stale }}</div>
              <div class="pulse-label">Going stale</div>
            </div>
            <div class="pulse-item">
              <div class="pulse-value">{{ pipeline.viewings }}</div>
              <div class="pulse-label">Viewings this week</div>
            </div>
            <div class="pulse-item pulse-item--accent">
              <div class="pulse-value">{{ pipeline.forecast }}</div>
              <div class="pulse-label">Commission forecast</div>
            </div>
          </div>
        </q-card>

        <!-- Fresh matches (prospect CRM) -->
        <q-card flat class="later-card" v-if="freshMatches.length > 0">
          <div class="later-card-header">
            <q-icon name="auto_awesome" size="16px" color="secondary" />
            <span>{{ freshMatches.length }} prospect{{ freshMatches.length === 1 ? '' : 's' }} matched new listings</span>
            <q-space />
            <q-btn flat dense no-caps size="sm" label="Review" color="primary" @click="$router.push('/people')" />
          </div>

          <q-list>
            <q-item
              v-for="match in freshMatches.slice(0, 3)"
              :key="match.id"
              clickable
              v-ripple
              @click="$router.push('/people')"
            >
              <q-item-section avatar>
                <q-avatar :color="isIos ? 'grey-3' : 'primary'" :text-color="isIos ? 'primary' : 'white'" :size="AVATAR_LIST">
                  {{ match.initials }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ match.prospectName }}</q-item-label>
                <q-item-label caption>matches {{ match.listingName }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge color="secondary" :label="`${match.score}%`" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

      </div>

      <!-- ── Footer padding for bottom tab bar ── -->
      <div class="tab-bar-spacer" />

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useQuasar } from 'quasar'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'
import { getDashboardSummary, type PropertyViewing } from '../services/api'
import { SPINNER_SIZE_PAGE, AVATAR_LIST, formatZAR } from '../utils/designTokens'

const auth   = useAuthStore()
const $q     = useQuasar()
const router = useRouter()
const { isIos } = usePlatform()

const setPageTitle = inject<(t: string | null) => void>('setPageTitle')

const loading = ref(true)
const upcomingViewings = ref<PropertyViewing[]>([])

// Earnings are computed on the backend in future — stubbed for now with realistic numbers
const earnings = ref({
  earned: 127400,
  target: 200000,
  targetPct: 64,
})

// Pipeline aggregate — stubbed until backend dashboard endpoint exposes these
const pipeline = ref({
  mandates: 14,
  stale: 3,
  viewings: 9,
  forecast: 'R 184k',
})

// Next move is AI-ranked on the backend in future — stubbed example
const nextMove = ref({
  id: 'match-bosch-1',
  title: '4 warm prospects match 14 Bosch St',
  subtitle: 'New listing published 2 hours ago. Best matches haven\'t been contacted.',
  impact: 28400,
  cta: 'Send to 4',
  action: 'review-matches',
})

// Fresh prospect matches — stubbed until prospect CRM backend lands
const freshMatches = ref([
  { id: 1, prospectName: 'John Dlamini',  listingName: '14 Bosch St',      initials: 'JD', score: 94 },
  { id: 2, prospectName: 'Nomvula Zulu',  listingName: '22 De Klerk Ave',  initials: 'NZ', score: 88 },
  { id: 3, prospectName: 'Andrew Meyer',  listingName: '14 Bosch St',      initials: 'AM', score: 81 },
])

function handleNextMove() {
  if (nextMove.value?.action === 'review-matches') {
    router.push('/people')
  }
}

function formatHour(iso: string): string {
  const d = new Date(iso)
  const h = d.getHours() % 12 || 12
  return String(h)
}

function formatMeridiem(iso: string): string {
  return new Date(iso).getHours() < 12 ? 'AM' : 'PM'
}

async function loadData(done?: () => void) {
  try {
    const res = await getDashboardSummary()
    const now = Date.now()
    upcomingViewings.value = (res.upcomingViewings ?? []).filter((v) => {
      const t = new Date(v.scheduled_at).getTime()
      return t >= now && t - now < 1000 * 60 * 60 * 24
    })
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load your day. Pull down to retry.', icon: 'error' })
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => {
  setPageTitle?.(`Today · ${auth.user?.first_name ?? 'Agent'}`)
  void loadData()
})
</script>

<style scoped lang="scss">
.today-page {
  background: var(--klikk-surface);
  padding: 16px 16px 0;
  min-height: 100vh;
}

/* ── Earnings hero ── */
.earnings-hero {
  background: linear-gradient(135deg, $primary 0%, #1b1d54 100%);
  color: white;
  border-radius: 16px;
  padding: 20px 20px 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(43, 45, 110, 0.18);
}

.earnings-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.72;
}

.earnings-value {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  margin-top: 6px;
}

.earnings-meta {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 4px;
}

.earnings-pct {
  font-size: 15px;
  font-weight: 700;
  color: $secondary;
}

.earnings-target {
  font-size: 13px;
  opacity: 0.7;
}

.earnings-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  margin-top: 12px;
  overflow: hidden;
}

.earnings-fill {
  height: 100%;
  background: $secondary;
  border-radius: 2px;
  transition: width 0.4s ease-out;
}

/* ── Next move ── */
.next-move-wrap {
  margin-bottom: 28px;
}

.next-move-eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--klikk-text-secondary);
  margin-bottom: 10px;
  padding-left: 2px;
}

.next-move-card {
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  box-shadow: var(--klikk-shadow-soft);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.next-move-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.next-move-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--klikk-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.3;
}

.next-move-sub {
  font-size: 13px;
  color: var(--klikk-text-secondary);
  line-height: 1.4;
}

.next-move-impact {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(20, 184, 166, 0.08);
  color: $positive;
  border-radius: 999px;
  font-size: 12px;
  width: fit-content;
  margin-top: 4px;

  strong {
    font-weight: 700;
  }
}

.next-move-cta {
  font-size: 15px;
  font-weight: 600;
  padding: 12px 0;
  letter-spacing: 0.01em;
}

.next-move-skeleton {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

/* ── Later ── */
.later-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.later-header {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--klikk-text-secondary);
  padding-left: 2px;
  margin-bottom: 2px;
}

.later-card {
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  box-shadow: var(--klikk-shadow-soft);
  overflow: hidden;
}

.later-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--klikk-text-primary);
  border-bottom: 1px solid var(--klikk-border);
}

.later-card-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  font-size: 13px;
  color: var(--klikk-text-secondary);
}

/* Viewing time ornament */
.viewing-time {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40px;
}

.viewing-time-hour {
  font-size: 18px;
  font-weight: 700;
  color: $primary;
  line-height: 1;
}

.viewing-time-meridiem {
  font-size: 10px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  letter-spacing: 0.05em;
  margin-top: 2px;
}

/* Pulse grid */
.pulse-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--klikk-border);
}

.pulse-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  background: white;
}

.pulse-item--warn .pulse-value {
  color: $warning;
}

.pulse-item--accent .pulse-value {
  color: $secondary;
}

.pulse-value {
  font-size: 22px;
  font-weight: 800;
  color: $primary;
  letter-spacing: -0.02em;
  line-height: 1;
}

.pulse-label {
  font-size: 11px;
  color: var(--klikk-text-secondary);
  font-weight: 500;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

/* Safe-area padding for bottom tab bar */
.tab-bar-spacer {
  height: calc(90px + env(safe-area-inset-bottom, 0px));
}
</style>

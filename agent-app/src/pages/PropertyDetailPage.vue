<template>
  <q-page v-if="property" :class="{ 'chat-active-page': mStore.activeRequest }">

    <!-- ── Tabs ────────────────────────────────────────────────────────────── -->
    <q-card flat class="tab-card" :class="mStore.activeRequest ? 'chat-active-card' : 'q-mx-md q-mt-sm'">
      <q-tabs
        v-show="!mStore.activeRequest"
        v-model="tab"
        dense
        align="justify"
        active-color="primary"
        indicator-color="primary"
        class="text-grey-7"
        no-caps
      >
        <q-tab name="info" label="Info" />
        <q-tab name="maintenance" label="Repairs" />
        <q-tab name="leases" label="Leases" />
        <q-tab name="viewings" label="Viewings" />
      </q-tabs>
      <q-separator v-show="!mStore.activeRequest" />

      <q-tab-panels v-model="tab" animated class="chat-panels">

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

            <q-item clickable v-ripple @click="tab = 'maintenance'" v-if="mStore.openCount > 0">
              <q-item-section avatar>
                <q-icon name="build" color="negative" size="20px" />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>Open repairs</q-item-label>
                <q-item-label class="text-negative text-weight-semibold">
                  {{ mStore.openCount }} open issue{{ mStore.openCount !== 1 ? 's' : '' }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-4" />
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

        <!-- ── MAINTENANCE tab ────────────────────────────────────────────── -->
        <q-tab-panel name="maintenance" class="q-pa-none">

          <!-- ── Chat view (request selected) ─────────────────────────────── -->
          <template v-if="mStore.activeRequest">
            <!-- Compact chat header — single row -->
            <div class="chat-header">
              <div class="row items-center no-wrap q-gutter-x-xs">
                <q-btn flat dense round icon="close" color="grey-7" size="sm" @click="mStore.clearSelection()" />
                <q-icon :name="maintenanceCategoryIcon(mStore.activeRequest.category)" color="grey-5" size="18px" />
                <div class="col min-width-0">
                  <div class="chat-header-title ellipsis">{{ mStore.activeRequest.title }}</div>
                  <div class="chat-header-sub ellipsis" v-if="mStore.activeRequest.tenant_name">
                    {{ mStore.activeRequest.tenant_name }}
                  </div>
                </div>
                <q-btn
                  outline no-caps
                  class="status-dropdown-btn flex-shrink-0"
                  :color="maintenanceStatusColor(mStore.activeRequest.status)"
                >
                  {{ fmtLabel(mStore.activeRequest.status) }}
                  <q-icon name="expand_more" size="18px" class="q-ml-xs" />
                  <q-menu class="status-menu">
                    <q-list style="min-width: 180px">
                      <q-item
                        v-if="mStore.activeRequest.status !== 'open'"
                        clickable v-ripple v-close-popup
                        @click="onUpdateStatus('open')"
                      >
                        <q-item-section avatar>
                          <q-avatar size="28px" color="info" text-color="white">
                            <q-icon name="radio_button_unchecked" size="16px" />
                          </q-avatar>
                        </q-item-section>
                        <q-item-section>
                          <q-item-label class="text-weight-medium">Open</q-item-label>
                          <q-item-label caption>Mark as open</q-item-label>
                        </q-item-section>
                      </q-item>
                      <q-item
                        v-if="mStore.activeRequest.status !== 'in_progress'"
                        clickable v-ripple v-close-popup
                        @click="onUpdateStatus('in_progress')"
                      >
                        <q-item-section avatar>
                          <q-avatar size="28px" color="warning" text-color="white">
                            <q-icon name="engineering" size="16px" />
                          </q-avatar>
                        </q-item-section>
                        <q-item-section>
                          <q-item-label class="text-weight-medium">In Progress</q-item-label>
                          <q-item-label caption>Work has started</q-item-label>
                        </q-item-section>
                      </q-item>
                      <q-item
                        v-if="mStore.activeRequest.status !== 'resolved'"
                        clickable v-ripple v-close-popup
                        @click="onUpdateStatus('resolved')"
                      >
                        <q-item-section avatar>
                          <q-avatar size="28px" color="positive" text-color="white">
                            <q-icon name="check_circle" size="16px" />
                          </q-avatar>
                        </q-item-section>
                        <q-item-section>
                          <q-item-label class="text-weight-medium">Resolved</q-item-label>
                          <q-item-label caption>Issue has been fixed</q-item-label>
                        </q-item-section>
                      </q-item>
                      <q-item
                        v-if="mStore.activeRequest.status !== 'closed'"
                        clickable v-ripple v-close-popup
                        @click="onUpdateStatus('closed')"
                      >
                        <q-item-section avatar>
                          <q-avatar size="28px" color="grey-5" text-color="white">
                            <q-icon name="cancel" size="16px" />
                          </q-avatar>
                        </q-item-section>
                        <q-item-section>
                          <q-item-label class="text-weight-medium">Closed</q-item-label>
                          <q-item-label caption>Close without fixing</q-item-label>
                        </q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </q-btn>
              </div>
            </div>
            <q-separator />

            <!-- Chat messages -->
            <div ref="chatContainer" class="chat-messages">
              <div v-if="mStore.loadingChat" class="row justify-center q-py-lg">
                <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
              </div>

              <template v-else-if="mStore.activities.length === 0">
                <div class="text-center q-pa-lg text-grey-5 text-body2">No messages yet.</div>
              </template>

              <template v-else>
                <template v-for="act in mStore.activities" :key="act.id">

                  <!-- Received (tenant / AI / other agent) -->
                  <div v-if="!isMine(act)" class="row justify-start q-mb-sm">
                    <div class="column" style="max-width: 82%">
                      <div
                        class="text-caption q-ml-sm q-mb-xs text-weight-semibold"
                        :style="{ color: senderColor(act) }"
                      >
                        {{ isAi(act) ? '🤖 AI Agent' : (act.created_by_name || 'Tenant') }}
                      </div>
                      <div class="chat-bubble-other">{{ stripAgentPrefix(act.message) }}</div>
                      <div class="text-caption text-grey-4 q-ml-sm q-mt-xs">{{ formatTime(act.created_at) }}</div>
                    </div>
                  </div>

                  <!-- Sent (mine) -->
                  <div v-else class="row justify-end q-mb-sm">
                    <div class="column items-end" style="max-width: 82%">
                      <div class="chat-bubble-user">{{ stripAgentPrefix(act.message) }}</div>
                      <div class="text-caption text-grey-4 q-mr-sm q-mt-xs">{{ formatTime(act.created_at) }}</div>
                    </div>
                  </div>

                </template>
              </template>
            </div>

            <!-- Chat input -->
            <div class="chat-input-bar q-pa-sm">
              <q-input
                v-model="chatMessage"
                dense
                outlined
                rounded
                placeholder="Type a message... (@agent for AI)"
                @keyup.enter="onSendMessage"
              >
                <template #append>
                  <q-btn
                    flat
                    dense
                    round
                    icon="send"
                    color="primary"
                    :disable="!chatMessage.trim()"
                    @click="onSendMessage"
                  />
                </template>
              </q-input>
            </div>
          </template>

          <!-- ── List view (no request selected) ──────────────────────────── -->
          <template v-else>
            <div v-if="mStore.loading" class="row justify-center q-py-lg">
              <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
            </div>

            <template v-else-if="mStore.requests.length === 0">
              <div class="empty-state">
                <q-icon name="build_circle" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
                <div class="empty-state-title">No maintenance requests</div>
              </div>
            </template>

            <template v-else>
              <!-- Filter toggle -->
              <div class="row items-center q-pa-sm q-gutter-x-sm">
                <q-chip
                  :outline="showClosed"
                  :color="showClosed ? 'grey-5' : 'primary'"
                  text-color="white"
                  size="sm"
                  clickable
                  @click="showClosed = false"
                  :label="`Open (${mStore.openCount})`"
                />
                <q-chip
                  v-if="mStore.closedRequests.length > 0"
                  :outline="!showClosed"
                  :color="showClosed ? 'primary' : 'grey-5'"
                  text-color="white"
                  size="sm"
                  clickable
                  @click="showClosed = true"
                  :label="`Resolved (${mStore.closedRequests.length})`"
                />
              </div>

              <div v-if="displayedRequests.length === 0" class="text-center q-pa-lg text-grey-5 text-body2">
                No {{ showClosed ? 'resolved' : 'open' }} issues
              </div>

              <q-list v-else separator>
                <q-item
                  v-for="req in displayedRequests"
                  :key="req.id"
                  clickable
                  v-ripple
                  @click="mStore.selectRequest(req.id)"
                >
                  <q-item-section avatar>
                    <q-avatar
                      :color="maintenancePriorityColor(req.priority)"
                      text-color="white"
                      :size="AVATAR_COMPACT"
                    >
                      <q-icon :name="maintenanceCategoryIcon(req.category)" size="20px" />
                    </q-avatar>
                  </q-item-section>

                  <q-item-section>
                    <q-item-label class="text-weight-medium">
                      {{ req.title }}
                      <q-icon
                        v-if="req.priority === 'urgent' || req.priority === 'high'"
                        name="priority_high"
                        :color="maintenancePriorityColor(req.priority)"
                        size="14px"
                        class="q-ml-xs"
                      />
                    </q-item-label>
                    <q-item-label caption v-if="req.tenant_name">
                      <q-icon name="person" size="12px" />
                      {{ req.tenant_name }}
                    </q-item-label>
                    <q-item-label caption class="text-grey-5">
                      {{ daysOpen(req.created_at) }}
                      <template v-if="mStore.unreadCount(req) > 0">
                        &middot; <span class="text-negative text-weight-semibold">{{ mStore.unreadCount(req) }} new</span>
                      </template>
                    </q-item-label>
                  </q-item-section>

                  <q-item-section side>
                    <q-badge
                      :color="maintenanceStatusColor(req.status)"
                      :label="fmtLabel(req.status)"
                    />
                  </q-item-section>
                </q-item>
              </q-list>
            </template>
          </template>
        </q-tab-panel>

        <!-- ── LEASES tab ─────────────────────────────────────────────────── -->
        <q-tab-panel name="leases" class="q-pa-none">
          <div v-if="loadingLeases" class="row justify-center q-py-lg">
            <q-spinner-dots color="primary" :size="SPINNER_SIZE_INLINE" />
          </div>

          <template v-else-if="propertyLeases.length === 0">
            <div class="empty-state">
              <q-icon name="description" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
              <div class="empty-state-title">No leases for this property</div>
              <div class="empty-state-action">
                <q-btn
                  unelevated
                  :rounded="isIos"
                  color="primary"
                  label="Create Lease"
                  icon="add"
                  size="sm"
                  @click="$router.push(`/properties/${id}/leases/new`)"
                />
              </div>
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
                  <q-badge :color="leaseStatusColor(lease.status)" :label="fmtLabel(lease.status)" />
                  <div class="text-caption text-weight-semibold text-positive">
                    R{{ formatZAR(lease.monthly_rent) }}/mo
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
            <div class="empty-state">
              <q-icon name="calendar_today" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
              <div class="empty-state-title">No viewings booked</div>
              <div class="empty-state-action">
                <q-btn flat color="secondary" label="Book viewing" size="sm"
                  @click="bookViewing()" />
              </div>
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
                <q-badge :color="statusColor(v.status)" :label="fmtLabel(v.status)" />
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

    <div v-if="!mStore.activeRequest" class="q-pb-xl" />

  </q-page>

  <q-page v-else-if="loading" class="row justify-center items-center">
    <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { getProperty, listViewings, listLeases, type Property, type PropertyViewing, type AgentLease } from '../services/api'
import { useMaintenanceStore } from '../stores/maintenance'
import { usePlatform } from '../composables/usePlatform'
import {
  statusColor, leaseStatusColor, formatDate, formatDateTimeShort, formatTime,
  daysRemaining, timeAgo, fmtLabel,
  maintenancePriorityColor, maintenanceStatusColor, maintenanceCategoryIcon,
} from '../utils/formatters'
import { SPINNER_SIZE_PAGE, SPINNER_SIZE_INLINE, EMPTY_ICON_SIZE, AVATAR_COMPACT, formatZAR } from '../utils/designTokens'
import type { MaintenanceActivity } from '../services/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ id: string }>()
const router = useRouter()
const $q = useQuasar()
const { isIos } = usePlatform()
const mStore = useMaintenanceStore()
const authStore = useAuthStore()
const setPageTitle = inject<(title: string | null) => void>('setPageTitle', () => {})

const tab             = ref('info')
const loading         = ref(true)
const loadingViewings = ref(false)
const loadingLeases   = ref(false)
const property        = ref<Property | null>(null)
const viewings        = ref<PropertyViewing[]>([])
const allLeases       = ref<AgentLease[]>([])
const chatMessage     = ref('')
const showClosed      = ref(false)
const chatContainer   = ref<HTMLElement | null>(null)

const availableCount = computed(() =>
  property.value?.units.filter((u) => u.status === 'available').length ?? 0,
)

const displayedRequests = computed(() =>
  showClosed.value ? mStore.closedRequests : mStore.openRequests,
)

const propertyLeases = computed(() =>
  allLeases.value.filter((l) => l.property_id === Number(props.id)),
)

const activeLeaseCount = computed(() =>
  propertyLeases.value.filter((l) => l.status === 'active').length,
)

const upcomingViewingCount = computed(() =>
  viewings.value.filter((v) => v.status === 'scheduled' || v.status === 'confirmed').length,
)

function daysOpen(created: string): string {
  const days = Math.floor((Date.now() - new Date(created).getTime()) / 86_400_000)
  if (days === 0) return 'Today'
  if (days === 1) return '1 day'
  return `${days} days`
}

function isMine(act: MaintenanceActivity): boolean {
  return act.created_by != null && Number(act.created_by) === Number(authStore.user?.id)
}

function isAi(act: MaintenanceActivity): boolean {
  return (
    act.metadata?.source === 'ai_agent' ||
    (act.activity_type === 'system' && act.created_by == null)
  )
}

const AGENT_PREFIX_RE = /^@agent\s*/i
function stripAgentPrefix(msg: string): string {
  return msg.replace(AGENT_PREFIX_RE, '')
}

// WhatsApp group-style: each participant gets a consistent color
const SENDER_COLORS = ['#1f7aec', '#e91e63', '#9c27b0', '#e65100', '#00897b', '#6a1b9a', '#c62828']
const _senderColorMap = new Map<string, string>()

function senderColor(act: MaintenanceActivity): string {
  if (isAi(act)) return '#25d366' // WhatsApp green for AI
  const key = act.created_by_name || String(act.created_by) || 'unknown'
  if (!_senderColorMap.has(key)) {
    _senderColorMap.set(key, SENDER_COLORS[_senderColorMap.size % SENDER_COLORS.length])
  }
  return _senderColorMap.get(key)!
}

function onSendMessage() {
  const msg = chatMessage.value.trim()
  if (!msg) return
  mStore.sendMessage(msg)
  chatMessage.value = ''
}

async function onUpdateStatus(status: 'open' | 'in_progress' | 'resolved' | 'closed') {
  if (!mStore.activeRequestId) return
  await mStore.updateStatus(mStore.activeRequestId, status)
}

function bookViewing(unitId?: number) {
  const query: Record<string, string> = { property: String(props.id) }
  if (unitId) query.unit = String(unitId)
  void router.push({ name: 'book-viewing', query })
}

// Auto-scroll chat when new messages arrive
watch(
  () => mStore.activities.length,
  () => {
    nextTick(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
    })
  },
)

// ── Data loading ─────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    property.value = await getProperty(Number(props.id))
    setPageTitle(property.value.name)

    loadingViewings.value = true
    loadingLeases.value   = true

    const [viewingsResp, leasesResp] = await Promise.allSettled([
      listViewings({ property: Number(props.id) }),
      listLeases(),
      mStore.fetchRequests(Number(props.id)),
    ])

    if (viewingsResp.status === 'fulfilled') viewings.value = viewingsResp.value.results
    if (leasesResp.status === 'fulfilled')   allLeases.value = leasesResp.value.results

    // Auto-switch to repairs if there are open issues
    if (mStore.openCount > 0) tab.value = 'maintenance'

    // Connect list WebSocket for real-time maintenance updates
    mStore.connectListSocket()
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load property.', icon: 'error' })
    void router.back()
  } finally {
    loading.value         = false
    loadingViewings.value = false
    loadingLeases.value   = false
  }
})

onUnmounted(() => {
  mStore.disconnect()
})
</script>

<style scoped lang="scss">
// ── Full-height chat page ──────────────────────────────────────────────────

.chat-active-page {
  padding: 0 !important;
  display: flex !important;
  flex-direction: column !important;
}

.chat-active-card {
  border-radius: 0 !important;
  border: none !important;
  margin: 0 !important;
  margin-bottom: 0 !important;
  flex: 1;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 44px - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px));
  max-height: calc(100dvh - 44px - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px));
  overflow: hidden;
}

// ── Tab card ────────────────────────────────────────────────────────────────

.tab-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  overflow-x: clip;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-panels {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;

  :deep(.q-panel) {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden !important;
    min-height: 0;
  }

  :deep(.q-tab-panel) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
}

// ── Maintenance chat styles ──────────────────────────────────────────────────

.chat-header {
  padding: 8px 10px;
  background: white;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
}

.chat-header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--klikk-text-primary);
  line-height: 1.3;
}

.chat-header-sub {
  font-size: 12.5px;
  color: var(--klikk-text-muted);
  line-height: 1.2;
}

.status-dropdown-btn {
  border-radius: 20px;
  padding: 4px 10px 4px 14px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  min-height: 32px;
  background: white !important;
  border-width: 1.5px;
}

.status-menu {
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);

  :deep(.q-item) {
    padding: 10px 16px;
    min-height: 52px;
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 10px 4px;
  background: white;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-height: 0;
}

.chat-input-bar {
  flex-shrink: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  background: white;
  padding: 8px 10px;
  padding-bottom: max(8px, env(safe-area-inset-bottom, 0px));
}
</style>

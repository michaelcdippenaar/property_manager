<!--
  AgencyShellView — portfolio dashboard (v2)

  Ported from docs/prototypes/admin-shell/index.html Dashboard route.
  Uses the new shared components (StatTile, Badge, AlertStrip, EventRow)
  and the useDashboardStore Pinia store (currently stubbed).

  Route: /agency-v2  (added alongside existing /agency view so we can
  compare side-by-side before flipping the default).
-->
<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  Zap, AlertCircle, Receipt, Wrench, CalendarDays, FileSignature,
  ClipboardList, ClipboardCheck, ShieldAlert, PenTool, Users,
  Bell, Inbox, TrendingUp,
} from 'lucide-vue-next'

import { useDashboardStore, type EventClass, type EventItem } from '../../stores/dashboard'
import StatTile from '../../components/shared/StatTile.vue'
import Badge from '../../components/shared/Badge.vue'
import AlertStrip from '../../components/shared/AlertStrip.vue'
import EventRow from '../../components/shared/EventRow.vue'

const router = useRouter()
const dashboard = useDashboardStore()

onMounted(() => {
  dashboard.load()
})

// Event class filter chips
const EVENT_CLASSES: { id: EventClass | null; label: string; icon: any }[] = [
  { id: null,         label: 'All',         icon: Inbox },
  { id: 'rent',       label: 'Rent',        icon: Receipt },
  { id: 'gate',       label: 'Gates',       icon: ShieldAlert },
  { id: 'maintenance',label: 'Maintenance', icon: Wrench },
  { id: 'renewal',    label: 'Renewals',    icon: TrendingUp },
  { id: 'refund',     label: 'Refunds',     icon: Receipt },
  { id: 'inspection', label: 'Inspections', icon: ClipboardCheck },
  { id: 'compliance', label: 'Compliance',  icon: AlertCircle },
  { id: 'signing',    label: 'Signing',     icon: FileSignature },
  { id: 'viewing',    label: 'Viewings',    icon: Users },
]

const gatePending = computed(() => dashboard.kpis.find(k => k.key === 'gate_pending'))

/**
 * Navigate to the most relevant detail view for the given event.
 * Uses the closest existing route per event class; deep-links to a specific
 * entity when a real propertyId is available on the event item.
 */
function handleEventAction(e: EventItem) {
  switch (e.eventClass) {
    case 'maintenance':
    case 'gate':
      router.push(e.propertyId
        ? { name: 'maintenance-detail', params: { id: e.propertyId } }
        : { name: 'maintenance-issues' })
      break
    case 'lease':
    case 'renewal':
    case 'signing':
      router.push({ name: 'leases' })
      break
    case 'rent':
    case 'refund':
      router.push({ name: 'payments' })
      break
    case 'inspection':
    case 'compliance':
    case 'viewing':
      // No dedicated route yet -- navigate to properties list.
      // Replace with a specific route when built.
      router.push({ name: 'properties' })
      break
    default:
      // Unknown future event class -- fail silently.
      break
  }
}
</script>

<template>
  <div class="space-y-5">
    <!-- ── Page header ── -->
    <header class="klikk-page-header">
      <div class="row">
        <div>
          <h1>Dashboard</h1>
          <p class="sub">Portfolio overview · all properties, all roles, one surface.</p>
        </div>
        <div class="actions">
          <button class="btn-outline">
            <Bell :size="14" /> Alerts
          </button>
          <RouterLink to="/properties" class="btn-outline">
            <CalendarDays :size="14" /> Calendar
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- ── Gate 3 alert strip (only if any pending) ── -->
    <AlertStrip
      v-if="gatePending && Number(gatePending.value) > 0"
      tone="warn"
    >
      <ShieldAlert :size="16" />
      <strong>{{ gatePending.value }} Gate{{ Number(gatePending.value) === 1 ? '' : 's' }} awaiting owner decision</strong>
      — oldest silent 25h · SLA breach in 23h
      <template #action>
        <RouterLink to="/maintenance" class="btn-outline">
          Review queue
        </RouterLink>
      </template>
    </AlertStrip>

    <!-- ── KPIs ── -->
    <section class="kpi-grid">
      <StatTile
        v-for="kpi in dashboard.kpis"
        :key="kpi.key"
        :label="kpi.label"
        :value="kpi.value"
        :suffix="kpi.suffix"
        :delta="kpi.delta"
        :tone="kpi.tone"
        :value-color="kpi.valueColor"
      />
    </section>

    <!-- ── Action queue + Upcoming side by side ── -->
    <div class="split">
      <!-- Action queue -->
      <div class="klikk-pcard">
        <h3>
          <Zap :size="16" />
          Action Queue
          <Badge tone="neutral" size="sm" style="margin-left:auto">
            {{ dashboard.filteredEvents.length }} items
          </Badge>
        </h3>

        <!-- Class filter -->
        <div class="filter-strip">
          <button
            v-for="cls in EVENT_CLASSES"
            :key="String(cls.id ?? 'all')"
            class="filter-chip"
            :class="{ active: dashboard.activeEventClass === cls.id }"
            @click="dashboard.setEventClass(cls.id)"
          >
            <component :is="cls.icon" :size="13" />
            {{ cls.label }}
            <span class="chip-count">
              {{ cls.id === null ? dashboard.events.length : (dashboard.eventCounts[cls.id] || 0) }}
            </span>
          </button>
        </div>

        <!-- Events -->
        <div class="events">
          <div v-if="dashboard.loading && !dashboard.loaded" class="empty">Loading…</div>
          <div v-else-if="dashboard.filteredEvents.length === 0" class="empty">
            Nothing here — enjoy the quiet.
          </div>
          <EventRow
            v-for="e in dashboard.filteredEvents"
            :key="e.id"
            :when="e.when"
            :tone="e.tone"
            :addr="e.addr"
            :ctx="e.ctx"
            :action="e.action"
            :primary="e.primary"
            @action="handleEventAction(e)"
          />
        </div>
      </div>

      <!-- Upcoming -->
      <div class="klikk-pcard">
        <h3>
          <CalendarDays :size="16" />
          Next 4 days
        </h3>
        <div class="upcoming">
          <div v-for="day in dashboard.upcoming" :key="day.day" class="up-day">
            <div class="up-day-label">{{ day.day }}</div>
            <div v-for="(row, idx) in day.rows" :key="idx" class="up-row">
              <span class="up-time">{{ row.time }}</span>
              <span class="up-body">
                <div class="up-title">{{ row.title }}</div>
                <div class="up-ctx">{{ row.ctx }}</div>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Kanban strip (portfolio state machine) ── -->
    <section class="klikk-pcard">
      <h3>
        <ClipboardList :size="16" />
        Portfolio state
        <span class="kanban-sub">lease lifecycle across {{ dashboard.kanban.reduce((n, c) => n + c.count, 0) }} leases</span>
      </h3>
      <div class="kanban-scroll">
        <div class="kanban">
          <div v-for="col in dashboard.kanban" :key="col.id" class="kcol">
            <div class="col-head">
              <span class="col-title">
                <span class="bullet" :style="{ background: col.bulletColor }" />
                {{ col.title }}
              </span>
              <span class="col-count">{{ col.count }}</span>
            </div>
            <div v-for="lead in col.leads" :key="lead.id" class="kcard">
              <div class="kcard-addr">{{ lead.addr }}</div>
              <div class="kcard-meta">
                <Badge
                  v-for="(m, i) in lead.meta"
                  :key="i"
                  tone="neutral"
                  size="sm"
                >{{ m }}</Badge>
              </div>
              <div v-if="lead.action" class="kcard-action" :class="lead.actionTone">
                {{ lead.action }} →
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── Outline button (page-header + alert actions) ───────────────────── */
.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid #EFEFF5;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #2B2D6E;
  cursor: pointer;
  transition: background .12s ease, border-color .12s ease;
  text-decoration: none;
}
.btn-outline:hover {
  background: #F5F5F8;
  border-color: #E1E1EB;
}

/* ── KPI grid ───────────────────────────────────────────────────────── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

/* ── Split (Action Queue + Upcoming) ────────────────────────────────── */
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}
@media (max-width: 1100px) {
  .split { grid-template-columns: 1fr; }
}

/* ── Filter strip (event class chips) ───────────────────────────────── */
.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid #EFEFF5;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #3b3e4e;
  background: #F5F5F8;
  border: 1px solid transparent;
  border-radius: 999px;
  cursor: pointer;
  transition: all .12s ease;
}
.filter-chip:hover { background: #EFEFF5; }
.filter-chip.active {
  background: #2B2D6E;
  color: #fff;
}
.filter-chip .chip-count {
  font-variant-numeric: tabular-nums;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(0,0,0,.08);
  font-size: 10px;
  font-weight: 600;
}
.filter-chip.active .chip-count { background: rgba(255,255,255,.18); }

/* ── Events list ────────────────────────────────────────────────────── */
.events { min-height: 120px; }
.empty {
  padding: 32px 14px;
  text-align: center;
  color: #6B6B7A;
  font-size: 13px;
}

/* ── Upcoming panel ─────────────────────────────────────────────────── */
.upcoming { padding: 4px 0; }
.up-day { padding: 10px 18px; border-bottom: 1px solid #EFEFF5; }
.up-day:last-child { border-bottom: none; }
.up-day-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #6B6B7A;
  margin-bottom: 8px;
}
.up-row {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 10px;
  padding: 6px 0;
  font-size: 12px;
}
.up-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #2B2D6E;
  font-weight: 500;
}
.up-title { font-weight: 500; color: #111; font-size: 13px; }
.up-ctx   { color: #6B6B7A; font-size: 12px; margin-top: 1px; }

/* ── Kanban ─────────────────────────────────────────────────────────── */
.kanban-sub {
  margin-left: auto;
  font-family: 'DM Sans', sans-serif;
  font-weight: 400;
  font-size: 12px;
  color: #6B6B7A;
}
.kanban-scroll {
  overflow-x: auto;
  padding: 14px 18px 18px;
}
.kanban {
  display: grid;
  grid-template-columns: repeat(8, minmax(220px, 1fr));
  gap: 12px;
  min-width: 1680px;
}
.kcol {
  background: #FAFAFC;
  border: 1px solid #EFEFF5;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px 6px;
}
.col-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: #3b3e4e;
}
.col-count {
  font-size: 11px;
  font-weight: 600;
  color: #6B6B7A;
  padding: 2px 8px;
  background: #EFEFF5;
  border-radius: 999px;
}
.bullet {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.kcard {
  background: #fff;
  border: 1px solid #EFEFF5;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: border-color .12s ease, box-shadow .12s ease;
}
.kcard:hover {
  border-color: #2B2D6E;
  box-shadow: 0 4px 12px rgba(43,45,110,.08);
}
.kcard-addr { font-size: 13px; font-weight: 600; color: #111; }
.kcard-meta { display: flex; flex-wrap: wrap; gap: 4px; }
.kcard-action {
  font-size: 11px;
  font-weight: 500;
  color: #2B2D6E;
  padding-top: 4px;
  border-top: 1px dashed #EFEFF5;
}
.kcard-action.warn { color: #d97706; }
.kcard-action.ok   { color: #0d9488; }
</style>

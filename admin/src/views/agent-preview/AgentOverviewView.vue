<!--
  AgentOverviewView — Dashboard

  1:1 port of docs/prototypes/admin-shell/index.html #route-dashboard.

  Renders inside AgentPreviewLayout's <main class="main"> — which lives
  inside `.agent-shell`, so every class used here (page-header, stats,
  events-layout, board-cols, etc) is already scoped and styled by
  /admin/src/assets/agent-shell.css.

  Three view panes toggled by the Events/Board/List segmented control:
    · Events — Action Queue (ev-menu + ev-list) + 14-day outlook (up-list)
    · Board  — 8-column lifecycle kanban (vacant → refund)
    · List   — flat tabular view of all events

  No Pinia — data is inlined to match the mockup exactly (30 events).
-->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Zap,
  LayoutGrid,
  List,
  Plus,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Wrench,
  UserCheck,
  Undo2,
  LogOut,
  LogIn,
  PenLine,
  BellRing,
  Eye,
  CheckSquare,
  RefreshCw,
  Home,
  Bed,
  Bath,
  Clock,
  ArrowRight,
  AlertTriangle,
  Check,
  ClipboardList,
} from 'lucide-vue-next'

const router = useRouter()

// ========== EVENT DATA MODEL (1:1 from mockup) ==========
interface EventType {
  key: string
  label: string
  group: 'urgent' | 'turnaround' | 'pipeline' | 'vacancy'
  ico: unknown  // Lucide component
  icoCls: string
  action: string
}

const EVENT_TYPES: EventType[] = [
  { key: 'rent-overdue',   label: 'Rent overdue',   group: 'urgent',     ico: AlertCircle,  icoCls: 'ev-ico-urgent',  action: 'Collect' },
  { key: 'maintenance',    label: 'Maintenance',    group: 'urgent',     ico: Wrench,       icoCls: 'ev-ico-maint',   action: 'Dispatch' },
  { key: 'owner-approval', label: 'Owner approval', group: 'urgent',     ico: UserCheck,    icoCls: 'ev-ico-gate',    action: 'Chase owner' },
  { key: 'deposit-refund', label: 'Deposit refund', group: 'urgent',     ico: Undo2,        icoCls: 'ev-ico-refund',  action: 'Refund' },
  { key: 'move-out',       label: 'Move-out',       group: 'turnaround', ico: LogOut,       icoCls: 'ev-ico-moveout', action: 'Inspect' },
  { key: 'move-in',        label: 'Move-in',        group: 'turnaround', ico: LogIn,        icoCls: 'ev-ico-movein',  action: 'Inspect' },
  { key: 'sign-contract',  label: 'Sign contract',  group: 'turnaround', ico: PenLine,      icoCls: 'ev-ico-sign',    action: 'Send to sign' },
  { key: 'notice',         label: 'Notice',         group: 'pipeline',   ico: BellRing,     icoCls: 'ev-ico-notice',  action: 'Acknowledge' },
  { key: 'viewings',       label: 'Viewings',       group: 'pipeline',   ico: Eye,          icoCls: 'ev-ico-view',    action: 'Host' },
  { key: 'screen',         label: 'Screen',         group: 'pipeline',   ico: CheckSquare,  icoCls: 'ev-ico-screen',  action: 'Review' },
  { key: 'renewal-due',    label: 'Renewal due',    group: 'pipeline',   ico: RefreshCw,    icoCls: 'ev-ico-renew',   action: 'Draft offer' },
  { key: 'no-contract',    label: 'No contract',    group: 'vacancy',    ico: Home,         icoCls: 'ev-ico-vacancy', action: 'List' },
]

interface Group { key: EventType['group']; label: string }
const GROUPS: Group[] = [
  { key: 'urgent',     label: 'Urgent' },
  { key: 'turnaround', label: 'Turnaround' },
  { key: 'pipeline',   label: 'Pipeline' },
  { key: 'vacancy',    label: 'Vacancy' },
]

interface EventItem { type: string; days: number; addr: string; ctx: string }
const EVENTS: EventItem[] = [
  // Urgent — rent overdue
  { type: 'rent-overdue',   days: -7, addr: '4 Church, Franschhoek',     ctx: 'R 18 750 unpaid · Abrahams family' },
  { type: 'rent-overdue',   days: -3, addr: '22 Plein, Stellenbosch',    ctx: 'R 13 500 unpaid · Jacobs, K.' },
  { type: 'rent-overdue',   days: -1, addr: 'Unit 5, Kloofzicht',        ctx: 'R 9 500 unpaid · Mthembu, L.' },
  // Urgent — maintenance
  { type: 'maintenance',    days: -2, addr: '8 Lourens, Somerset West',  ctx: 'Kaap Damp · day 4 on site · SLA breach' },
  { type: 'maintenance',    days: 0,  addr: '4 Church, Franschhoek',     ctx: 'Gate motor quote overdue from supplier' },
  { type: 'maintenance',    days: 1,  addr: '15 Andringa, Stellenbosch', ctx: 'EZ Locksmith · ETA 11:00' },
  { type: 'maintenance',    days: 2,  addr: '12 Dorp, Stellenbosch',     ctx: 'Leaking tap · no quote yet' },
  // Urgent — owner approval
  { type: 'owner-approval', days: -1, addr: '22 Plein, Stellenbosch',    ctx: 'Gate 3 · Geyser R 8 200 · owner unresponsive 25h' },
  { type: 'owner-approval', days: 0,  addr: '33 Ryneveld, Stellenbosch', ctx: 'Gate 1 · listing approval · draft ready' },
  // Urgent — deposit refund
  { type: 'deposit-refund', days: -4, addr: '3 Dorp, Stellenbosch',      ctx: 'R 24 000 held · Pienaar · RHA 14d left' },
  // Turnaround — move-out
  { type: 'move-out',       days: 2,  addr: '25 Bird, Stellenbosch',     ctx: 'Outgoing · Smit vacating 25 Apr' },
  // Turnaround — move-in
  { type: 'move-in',        days: 5,  addr: '22 Plein, Stellenbosch',    ctx: 'Ingoing inspection · Jacobs 1 May' },
  { type: 'move-in',        days: 12, addr: '19 Main, Stellenbosch',     ctx: 'Ingoing · Mthembu renewal 8 May' },
  // Turnaround — sign
  { type: 'sign-contract',  days: -1, addr: '22 Plein, Stellenbosch',    ctx: 'Tenant signed · owner countersign · SLA 18h' },
  { type: 'sign-contract',  days: 3,  addr: '8 Lourens, Somerset West',  ctx: 'Lease ready · send to tenant' },
  // Pipeline — notice
  { type: 'notice',         days: -5, addr: '25 Bird, Stellenbosch',     ctx: '2-month notice from Smit · acknowledge' },
  // Pipeline — viewings
  { type: 'viewings',       days: 1,  addr: '33 Ryneveld, Stellenbosch', ctx: 'Open house · 3 booked · Sarah host' },
  { type: 'viewings',       days: 3,  addr: 'Unit 5, Kloofzicht',        ctx: 'Individual slot · 1 booked' },
  { type: 'viewings',       days: 4,  addr: '7A Paul Kruger, Paarl',     ctx: 'Open house · 2 booked' },
  { type: 'viewings',       days: 8,  addr: '12 Dorp, Stellenbosch',     ctx: 'Individual slots · 4 booked' },
  { type: 'viewings',       days: 10, addr: '33 Ryneveld, Stellenbosch', ctx: 'Second open house' },
  // Pipeline — screen
  { type: 'screen',         days: 0,  addr: '8 Lourens, Somerset West',  ctx: '2 applications · run credit check' },
  { type: 'screen',         days: 1,  addr: '33 Ryneveld, Stellenbosch', ctx: '3 applications · shortlist review' },
  { type: 'screen',         days: 4,  addr: 'Unit 5, Kloofzicht',        ctx: '1 application · waiting on payslips' },
  // Pipeline — renewal
  { type: 'renewal-due',    days: 14, addr: '19 Main, Stellenbosch',     ctx: 'Lease ends 30 Jun · Mthembu · draft offer' },
  { type: 'renewal-due',    days: 45, addr: '4 Church, Franschhoek',     ctx: 'Lease ends 31 Aug · Abrahams' },
  // Vacancy
  { type: 'no-contract',    days: -12, addr: '12 Dorp, Stellenbosch',    ctx: 'Vacant 12 days · R 12 500/mo potential' },
  { type: 'no-contract',    days: -3,  addr: '7A Paul Kruger, Paarl',    ctx: 'Vacant 3 days · list for marketing' },
  { type: 'no-contract',    days: -21, addr: 'Erf 702, Franschhoek',     ctx: 'DRAFT · mandate not signed' },
  { type: 'no-contract',    days: -5,  addr: 'Unit 11, Winelands Est.',  ctx: 'ON_HOLD · owner paused 5 days' },
]

// ========== STATE ==========
const view = ref<'events' | 'board' | 'list'>('events')
const selectedKey = ref<string>('rent-overdue')

// ========== HELPERS ==========
function whenFmt(days: number): { text: string; cls: string } {
  if (days < 0) return { text: `Overdue ${-days}d`, cls: 'overdue' }
  if (days === 0) return { text: 'Today', cls: 'today' }
  if (days === 1) return { text: 'Tomorrow', cls: 'today' }
  if (days <= 7) return { text: `in ${days}d`, cls: 'soon' }
  return { text: `in ${days}d`, cls: 'future' }
}

function groupDayLabel(days: number): string {
  if (days < 0) return 'Overdue'
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString('en-ZA', { weekday: 'short', day: 'numeric', month: 'short' })
}

// Map ev-ico-* class to CSS variable colour for the outlook dots
function dotColor(icoCls: string): string {
  const map: Record<string, string> = {
    'ev-ico-urgent':  'var(--danger)',
    'ev-ico-maint':   'var(--warn)',
    'ev-ico-gate':    '#8B5CF6',
    'ev-ico-refund':  'var(--accent)',
    'ev-ico-moveout': '#D97706',
    'ev-ico-movein':  'var(--ok)',
    'ev-ico-sign':    'var(--info)',
    'ev-ico-notice':  'var(--muted)',
    'ev-ico-view':    '#14B8A6',
    'ev-ico-screen':  'var(--navy)',
    'ev-ico-renew':   '#EA580C',
    'ev-ico-vacancy': 'var(--muted)',
  }
  return map[icoCls] ?? 'var(--muted)'
}

// ========== KPIs ==========
const kTotal   = computed(() => EVENTS.length)
const kOverdue = computed(() => EVENTS.filter(e => e.days < 0).length)
const kToday   = computed(() => EVENTS.filter(e => e.days >= 0 && e.days <= 1).length)
const kWeek    = computed(() => EVENTS.filter(e => e.days >= 0 && e.days <= 7).length)

// ========== ACTION QUEUE ==========
const eventCounts = computed<Record<string, number>>(() => {
  const out: Record<string, number> = {}
  EVENT_TYPES.forEach(t => { out[t.key] = EVENTS.filter(e => e.type === t.key).length })
  return out
})

const selectedType = computed(() => EVENT_TYPES.find(t => t.key === selectedKey.value)!)

const selectedEvents = computed(() =>
  EVENTS
    .filter(e => e.type === selectedKey.value)
    .sort((a, b) => a.days - b.days)
)

function selectKey(k: string) { selectedKey.value = k }

// ========== 14-DAY OUTLOOK ==========
interface OutlookDay { days: number; label: string; items: EventItem[] }

const outlookDays = computed<OutlookDay[]>(() => {
  const bucket: Record<number, EventItem[]> = {}
  EVENTS.forEach(e => {
    if (e.days > 14) return
    const key = Math.max(e.days, -1) // collapse overdue into -1
    if (!bucket[key]) bucket[key] = []
    bucket[key].push(e)
  })
  return Object.keys(bucket)
    .map(Number)
    .sort((a, b) => a - b)
    .map(k => ({
      days: k,
      label: k === -1 ? 'Overdue' : groupDayLabel(k),
      items: bucket[k],
    }))
})

function outlookTypeFor(ev: EventItem): EventType {
  return EVENT_TYPES.find(t => t.key === ev.type)!
}

// ========== LIST VIEW ==========
interface StateMapEntry { label: string; color: string }
const STATE_MAP: Record<string, StateMapEntry> = {
  'rent-overdue':   { label: 'Active',   color: 'var(--ok)' },
  'maintenance':    { label: 'Active',   color: 'var(--ok)' },
  'sign-contract':  { label: 'Signing',  color: 'var(--warn)' },
  'screen':         { label: 'Applied',  color: '#8B5CF6' },
  'viewings':       { label: 'Marketing', color: 'var(--info)' },
  'move-in':        { label: 'Active',   color: 'var(--ok)' },
  'move-out':       { label: 'Move-out', color: 'var(--accent)' },
  'deposit-refund': { label: 'Refund',   color: 'var(--danger)' },
  'no-contract':    { label: 'Vacant',   color: 'var(--muted-2)' },
  'renewal-due':    { label: 'Renewal',  color: '#D97706' },
  'notice':         { label: 'Active',   color: 'var(--ok)' },
  'owner-approval': { label: 'Signing',  color: 'var(--warn)' },
}

const listRows = computed(() =>
  EVENTS.slice(0, 20).map(e => {
    const st = STATE_MAP[e.type] ?? { label: '—', color: 'var(--muted)' }
    const t = EVENT_TYPES.find(x => x.key === e.type)!
    const w = whenFmt(e.days)
    const tenant = e.ctx.split('·')[1]?.trim() ?? '—'
    const whenColor =
      w.cls === 'overdue' ? 'var(--danger)' :
      w.cls === 'today' ? 'var(--warn)' : 'var(--ink)'
    return { e, st, t, w, tenant, whenColor }
  })
)

function gotoProperty() {
  router.push('/agent/property')
}
</script>

<template>
  <section>
    <!-- Page header -->
    <div class="page-header">
      <div class="breadcrumb"><span>Dashboard</span></div>
      <div class="page-header-row">
        <div>
          <h1>Good morning, MC</h1>
          <p class="sub">47 properties · 89.4% occupied · 6 items need you today</p>
        </div>
        <div class="page-actions">
          <div class="view-toggle">
            <button :class="{ active: view === 'events' }" @click="view = 'events'" aria-label="Events view">
              <Zap :size="14" />Events
            </button>
            <button :class="{ active: view === 'board' }" @click="view = 'board'" aria-label="Board view">
              <LayoutGrid :size="14" />Board
            </button>
            <button :class="{ active: view === 'list' }" @click="view = 'list'" aria-label="List view">
              <List :size="14" />List
            </button>
          </div>
          <button class="btn primary" type="button" aria-label="Add property">
            <Plus :size="14" />Add property
          </button>
        </div>
      </div>
    </div>

    <!-- KPIs -->
    <div class="stats">
      <div class="stat">
        <div class="label">Total events</div>
        <div class="value">{{ kTotal }}</div>
        <div class="delta">across portfolio</div>
      </div>
      <div class="stat">
        <div class="label">Overdue</div>
        <div class="value" style="color:var(--danger)">{{ kOverdue }}</div>
        <div class="delta down">needs attention</div>
      </div>
      <div class="stat">
        <div class="label">Today + tomorrow</div>
        <div class="value" style="color:var(--warn)">{{ kToday }}</div>
        <div class="delta">next 48h</div>
      </div>
      <div class="stat">
        <div class="label">This week</div>
        <div class="value">{{ kWeek }}</div>
        <div class="delta">7-day outlook</div>
      </div>
    </div>

    <!-- ================ EVENTS VIEW ================ -->
    <div v-if="view === 'events'">
      <div class="events-layout">
        <!-- Action Queue -->
        <div class="events-card">
          <div class="events-head">
            <Zap :size="14" style="color:var(--navy)" />
            <span class="events-head-title">Action Queue</span>
            <span class="events-head-sub">{{ selectedEvents.length }} · {{ selectedType.label }}</span>
          </div>
          <div class="events-grid">
            <!-- Menu -->
            <div class="ev-menu">
              <template v-for="g in GROUPS" :key="g.key">
                <h4>{{ g.label }}</h4>
                <button
                  v-for="t in EVENT_TYPES.filter(x => x.group === g.key)"
                  :key="t.key"
                  class="ev-item"
                  :class="{ active: t.key === selectedKey }"
                  type="button"
                  :aria-label="`${t.label}: ${eventCounts[t.key] || 0} items`"
                  @click="selectKey(t.key)"
                >
                  <span class="ev-ico-sq" :class="t.icoCls">
                    <component :is="t.ico" :size="14" />
                  </span>
                  <span>{{ t.label }}</span>
                  <span class="ev-count">{{ eventCounts[t.key] || 0 }}</span>
                </button>
              </template>
            </div>

            <!-- List -->
            <div class="ev-list">
              <template v-if="selectedEvents.length === 0">
                <div style="padding:40px;text-align:center;color:var(--muted)">
                  <CheckCircle2 :size="32" style="display:block;margin:0 auto 8px" />
                  <p>All clear. Nothing pending in "{{ selectedType.label }}".</p>
                </div>
              </template>
              <div
                v-for="(r, i) in selectedEvents"
                :key="`${r.addr}-${i}`"
                class="ev-row"
                @click="gotoProperty"
              >
                <span class="ev-when" :class="whenFmt(r.days).cls">
                  <span class="bullet" />{{ whenFmt(r.days).text }}
                </span>
                <div>
                  <div class="ev-ctx-addr">{{ r.addr }}</div>
                  <div class="ev-ctx-sub">{{ r.ctx }}</div>
                </div>
                <button class="ev-act" type="button" @click.stop="gotoProperty">
                  {{ selectedType.action }} →
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 14-day outlook -->
        <aside class="events-card up-card">
          <div class="events-head">
            <Calendar :size="14" style="color:var(--navy)" />
            <span class="events-head-title">14-day Outlook</span>
          </div>
          <div class="up-list">
            <div v-for="d in outlookDays" :key="d.days" class="up-day">
              <div class="up-day-label">
                <span>{{ d.label }}</span>
                <span class="count">{{ d.items.length }}</span>
              </div>
              <div class="up-day-items">
                <span
                  v-for="(it, i) in d.items.slice(0, 6)"
                  :key="i"
                  class="ev-dot"
                  :style="{ background: dotColor(outlookTypeFor(it).icoCls) }"
                  :title="outlookTypeFor(it).label"
                />
                {{ d.items.slice(0, 3).map(i => i.addr.split(',')[0]).join(' · ') }}<span v-if="d.items.length > 3">
                  +{{ d.items.length - 3 }}</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- ================ BOARD VIEW ================ -->
    <div v-else-if="view === 'board'">
      <div class="board">
        <div class="board-cols">
          <!-- Vacant -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-vacant" />Vacant</div>
              <div class="col-count">4</div>
            </div>
            <div class="card" @click="gotoProperty">
              <div class="card-addr">12 Dorp St, Stellenbosch</div>
              <div class="card-meta">
                <span class="tag"><Bed :size="12" />2</span>
                <span class="tag"><Bath :size="12" />1</span>
                <span class="tag">R 12 500</span>
              </div>
              <div class="card-action warn"><Clock :size="12" />Vacant 12 days</div>
            </div>
            <div class="card">
              <div class="card-addr">7A Paul Kruger, Paarl</div>
              <div class="card-meta">
                <span class="tag"><Bed :size="12" />3</span>
                <span class="tag">R 17 800</span>
              </div>
              <div class="card-action neutral"><ArrowRight :size="12" />List for marketing</div>
            </div>
          </div>

          <!-- Marketing -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-marketing" />Marketing</div>
              <div class="col-count">6</div>
            </div>
            <div class="card">
              <div class="card-addr">33 Ryneveld, Stellenbosch</div>
              <div class="card-meta">
                <span class="tag"><Bed :size="12" />2</span>
                <span class="tag">R 14 000</span>
              </div>
              <div class="card-action"><Calendar :size="12" />3 viewings booked</div>
            </div>
            <div class="card">
              <div class="card-addr">Unit 5, Kloofzicht</div>
              <div class="card-meta">
                <span class="tag"><Bed :size="12" />1</span>
                <span class="tag">R 9 500</span>
              </div>
              <div class="card-action neutral"><Eye :size="12" />18 listing views</div>
            </div>
          </div>

          <!-- Applied -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-applied" />Applied</div>
              <div class="col-count">3</div>
            </div>
            <div class="card">
              <div class="card-addr">8 Lourens St, Somerset W.</div>
              <div class="card-meta"><span class="tag">2 applications</span></div>
              <div class="card-action"><UserCheck :size="12" />Review credit checks</div>
            </div>
          </div>

          <!-- Signing -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-signing" />Signing</div>
              <div class="col-count">2</div>
            </div>
            <div class="card">
              <div class="card-addr">22 Plein, Stellenbosch</div>
              <div class="card-meta"><span class="tag">Awaiting countersign</span></div>
              <div class="card-action warn"><Clock :size="12" />SLA 18h</div>
            </div>
          </div>

          <!-- Active -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-active" />Active</div>
              <div class="col-count">28</div>
            </div>
            <div class="card" @click="gotoProperty">
              <div class="card-addr">15 Andringa, Stellenbosch</div>
              <div class="card-meta">
                <span class="tag">Vink family</span>
                <span class="tag">R 15 200/mo</span>
              </div>
              <div class="card-action ok"><Check :size="12" />Rent paid</div>
            </div>
            <div class="card">
              <div class="card-addr">4 Church, Franschhoek</div>
              <div class="card-meta">
                <span class="tag">Abrahams</span>
                <span class="tag">R 18 750/mo</span>
              </div>
              <div class="card-action warn"><AlertTriangle :size="12" />Rent 3d late</div>
            </div>
            <div class="card">
              <div class="card-addr">Unit 12, Winelands Estate</div>
              <div class="card-meta">
                <span class="tag">Nel</span>
                <span class="tag">R 11 000/mo</span>
              </div>
              <div class="card-action ok"><Check :size="12" />Rent paid</div>
            </div>
          </div>

          <!-- Renewal -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-renewal" />Renewal due</div>
              <div class="col-count">2</div>
            </div>
            <div class="card">
              <div class="card-addr">19 Main, Stellenbosch</div>
              <div class="card-meta"><span class="tag">Lease ends 30 Jun</span></div>
              <div class="card-action"><RefreshCw :size="12" />Send offer (T-60)</div>
            </div>
          </div>

          <!-- Move-out -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-moveout" />Move-out</div>
              <div class="col-count">1</div>
            </div>
            <div class="card">
              <div class="card-addr">25 Bird, Stellenbosch</div>
              <div class="card-meta"><span class="tag">Notice given 14 Apr</span></div>
              <div class="card-action"><ClipboardList :size="12" />Book outgoing insp.</div>
            </div>
          </div>

          <!-- Refund -->
          <div class="col">
            <div class="col-head">
              <div class="col-title"><span class="bullet state-bullet-refund" />Refund</div>
              <div class="col-count">1</div>
            </div>
            <div class="card">
              <div class="card-addr">3 Dorp, Stellenbosch</div>
              <div class="card-meta"><span class="tag">Deposit R 24 000</span></div>
              <div class="card-action warn"><Clock :size="12" />RHA clock: 14d left</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ================ LIST VIEW ================ -->
    <div v-else>
      <div class="table-wrap" style="padding-top:12px">
        <table class="data">
          <thead>
            <tr>
              <th scope="col">Address</th>
              <th scope="col">State</th>
              <th scope="col">Tenant</th>
              <th scope="col">Rent</th>
              <th scope="col">Next action</th>
              <th scope="col">Agent</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in listRows" :key="i" @click="gotoProperty">
              <td><strong>{{ row.e.addr }}</strong></td>
              <td>
                <span class="badge">
                  <span class="bullet" :style="{ background: row.st.color }" />{{ row.st.label }}
                </span>
              </td>
              <td>{{ row.tenant }}</td>
              <td class="money">—</td>
              <td>
                <span :style="{ color: row.whenColor }">
                  {{ row.t.action }} · {{ row.w.text }}
                </span>
              </td>
              <td>Sarah N.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

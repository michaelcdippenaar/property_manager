/**
 * dashboard store — Agency dashboard data (KPIs, events, kanban, upcoming)
 *
 * STUB IMPLEMENTATION — returns mock data matching the admin-shell mockup.
 * When ready to wire to real APIs, swap the body of `load()` for `api.get(...)`
 * calls. The shape of the returned data is intentionally 1:1 with what the
 * backend is expected to serve per the `Projects/Property_Manager/Agent/dashboards.md`
 * spec, so downstream components don't change when the stub is replaced.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// ── Types (match Projects/Property_Manager/Agent/dashboards.md data contract) ──

export type WhenTone = 'overdue' | 'today' | 'soon' | 'future'
export type EventClass =
  | 'rent'
  | 'maintenance'
  | 'lease'
  | 'renewal'
  | 'refund'
  | 'inspection'
  | 'compliance'
  | 'gate'
  | 'signing'
  | 'viewing'

export interface KPI {
  key: string
  label: string
  value: string | number
  suffix?: string
  delta?: string
  tone?: 'neutral' | 'up' | 'down' | 'warn' | 'danger'
  valueColor?: string
}

export interface EventItem {
  id: string
  eventClass: EventClass
  when: string
  tone: WhenTone
  addr: string
  ctx: string
  action?: string
  primary?: boolean
  propertyId?: string
}

export interface KanbanLead {
  id: string
  addr: string
  meta: string[]
  action?: string
  actionTone?: 'neutral' | 'warn' | 'ok'
}

export interface KanbanCol {
  id: string
  title: string
  count: number
  bulletColor: string
  leads: KanbanLead[]
}

export interface UpcomingDay {
  day: string
  rows: { time: string; title: string; ctx: string; icon?: string }[]
}

// ── Store ──

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref<string | null>(null)

  const kpis = ref<KPI[]>([])
  const events = ref<EventItem[]>([])
  const kanban = ref<KanbanCol[]>([])
  const upcoming = ref<UpcomingDay[]>([])

  // Event-class filter for the Action Queue. `null` = all.
  const activeEventClass = ref<EventClass | null>(null)

  const filteredEvents = computed(() => {
    if (!activeEventClass.value) return events.value
    return events.value.filter(e => e.eventClass === activeEventClass.value)
  })

  const eventCounts = computed(() => {
    const counts: Record<string, number> = { all: events.value.length }
    for (const e of events.value) {
      counts[e.eventClass] = (counts[e.eventClass] || 0) + 1
    }
    return counts
  })

  /**
   * Load dashboard data.
   *
   * Currently returns stub data hard-coded to match the admin-shell mockup.
   * Replace this with API calls when endpoints are ready, e.g.:
   *   const [k, e, kb, up] = await Promise.all([
   *     api.get('/dashboard/kpis'),
   *     api.get('/dashboard/events'),
   *     api.get('/dashboard/kanban'),
   *     api.get('/dashboard/upcoming'),
   *   ])
   */
  async function load() {
    loading.value = true
    error.value = null
    try {
      // Simulate network so loading states actually flash
      await new Promise(resolve => setTimeout(resolve, 120))

      kpis.value = STUB_KPIS
      events.value = STUB_EVENTS
      kanban.value = STUB_KANBAN
      upcoming.value = STUB_UPCOMING
      loaded.value = true
    } catch (err: any) {
      error.value = err?.message || 'Failed to load dashboard'
    } finally {
      loading.value = false
    }
  }

  function setEventClass(cls: EventClass | null) {
    activeEventClass.value = cls
  }

  return {
    // state
    loading,
    loaded,
    error,
    kpis,
    events,
    kanban,
    upcoming,
    activeEventClass,
    // getters
    filteredEvents,
    eventCounts,
    // actions
    load,
    setEventClass,
  }
})

// ─────────────────────────────────────────────────────────────────────────────
// STUB DATA — mirrors docs/prototypes/admin-shell/index.html Dashboard route.
// Replace with API calls when backend endpoints are live.
// ─────────────────────────────────────────────────────────────────────────────

const STUB_KPIS: KPI[] = [
  { key: 'portfolio',   label: 'Portfolio',       value: 134,     delta: '128 let · 6 vacant · 95.5% occ.', tone: 'neutral' },
  { key: 'arrears',     label: 'Arrears',         value: 'R 48 200', delta: '6 tenants · R 12.8k oldest',   tone: 'down'    },
  { key: 'due_this_wk', label: 'Actions due',     value: 18,      delta: '3 overdue · 4 today · 11 soon',   tone: 'warn'    },
  { key: 'gate_pending',label: 'Gates pending',   value: 4,       delta: 'G3 × 2 · G5 × 1 · G6 × 1',        tone: 'warn', valueColor: '#7C3AED' },
  { key: 'collections', label: 'Collected MTD',   value: 'R 1.42m', delta: '94.2% of billed',               tone: 'up'      },
  { key: 'commission',  label: 'Commission MTD',  value: 'R 128k', delta: '+11% vs last month',             tone: 'up'      },
]

const STUB_EVENTS: EventItem[] = [
  // Rent
  { id: 'e1',  eventClass: 'rent', tone: 'overdue', when: '3d overdue', addr: '15 Andringa',       ctx: 'Rent overdue · R 12 800 · Piet Vink',     action: 'Chase tenant', primary: true },
  { id: 'e2',  eventClass: 'rent', tone: 'overdue', when: '2d overdue', addr: '8 Lourens',         ctx: 'Rent overdue · R 9 400 · Smit family',    action: 'Chase tenant' },
  { id: 'e3',  eventClass: 'rent', tone: 'today',   when: 'Today',      addr: '22 Plein',          ctx: 'Rent due today · R 14 500 · Jacobs',      action: 'Send reminder' },
  // Gate 3
  { id: 'e4',  eventClass: 'gate', tone: 'overdue', when: '25h silent', addr: '22 Plein',          ctx: 'Gate 3 · geyser quote R 8 200 · owner Merwe', action: 'Chase owner', primary: true },
  { id: 'e5',  eventClass: 'gate', tone: 'soon',    when: 'SLA 23h',    addr: '33 Ryneveld',       ctx: 'Gate 3 · paint R 3 600 · auto-approved',  action: 'Dispatch' },
  // Maintenance
  { id: 'e6',  eventClass: 'maintenance', tone: 'today', when: 'Today 11:00', addr: '15 Andringa', ctx: 'EZ Locksmith · door lock #228 · tenant on site', action: 'Confirm' },
  { id: 'e7',  eventClass: 'maintenance', tone: 'soon',  when: 'Fri 09:00',   addr: '7A Paul Kruger', ctx: 'BluWater · pool pump #223 · key pickup', action: 'Arrange access' },
  // Renewal
  { id: 'e8',  eventClass: 'renewal',     tone: 'soon',  when: '60d',         addr: '4 Church, Franschhoek', ctx: 'Lease ends 17 Jun · Mthembu family', action: 'Prepare renewal' },
  { id: 'e9',  eventClass: 'renewal',     tone: 'future',when: '90d',         addr: '19 Main, Stelle.',      ctx: 'Lease ends 18 Jul · Pienaar',         action: 'Flag' },
  // Refund
  { id: 'e10', eventClass: 'refund',      tone: 'today', when: 'Day 14/21',   addr: '3 Dorp, Stelle.',       ctx: 'Deduction statement due · R 4 790', action: 'Send statement', primary: true },
  { id: 'e11', eventClass: 'refund',      tone: 'soon',  when: 'Day 7/21',    addr: '25 Bird, Stelle.',      ctx: 'Clean exit · refund in full',       action: 'Release' },
  // Inspection
  { id: 'e12', eventClass: 'inspection',  tone: 'today', when: 'Today 14:00', addr: '19 Main',               ctx: 'Ingoing · Mthembu renewal',         action: 'Open' },
  { id: 'e13', eventClass: 'inspection',  tone: 'soon',  when: 'Fri 10:00',   addr: '4 Church',              ctx: 'Mid-tenancy condition check',       action: 'Open' },
  // Compliance
  { id: 'e14', eventClass: 'compliance',  tone: 'overdue', when: 'COC 14d expired', addr: '12 Dorp',         ctx: 'Electrical CoC expired — renew',    action: 'Order cert', primary: true },
  { id: 'e15', eventClass: 'compliance',  tone: 'soon',  when: 'FICA 30d',    addr: 'Owner · J. van der M.', ctx: 'FICA re-verification due',          action: 'Request docs' },
  // Signing
  { id: 'e16', eventClass: 'signing',     tone: 'today', when: 'Today',       addr: '22 Plein',              ctx: 'Lease signed by tenant · awaiting owner', action: 'Remind owner' },
  // Viewing
  { id: 'e17', eventClass: 'viewing',     tone: 'soon',  when: 'Sat 11:00',   addr: '33 Ryneveld',           ctx: '3 applicants booked · vacant',      action: 'Prep pack' },
]

const STUB_KANBAN: KanbanCol[] = [
  {
    id: 'vacant', title: 'Vacant', count: 6, bulletColor: '#6B6B7A',
    leads: [
      { id: 'k1', addr: '33 Ryneveld · 2-bed',    meta: ['R 11 500', '14d vacant'], action: 'Market',   actionTone: 'neutral' },
      { id: 'k2', addr: '12 Dorp · 3-bed house',  meta: ['R 18 900', '3d vacant'],  action: 'Photos',   actionTone: 'neutral' },
    ],
  },
  {
    id: 'marketing', title: 'Marketing', count: 4, bulletColor: '#2B2D6E',
    leads: [
      { id: 'k3', addr: '25 Bird · 1-bed studio', meta: ['Listed 3 portals', '7 enquiries'], action: '2 viewings booked', actionTone: 'ok' },
      { id: 'k4', addr: '7A Paul Kruger · 3-bed', meta: ['Listed 2 portals', '12 enquiries'], action: 'Schedule viewings', actionTone: 'warn' },
    ],
  },
  {
    id: 'applied', title: 'Applied', count: 3, bulletColor: '#14b8a6',
    leads: [
      { id: 'k5', addr: '25 Bird · Jansen family', meta: ['Credit 720', 'Income R 48k'], action: 'Screening', actionTone: 'neutral' },
      { id: 'k6', addr: '7A Paul Kruger · Mthembu', meta: ['Credit 680', 'Income R 62k'], action: 'Tenant checks', actionTone: 'neutral' },
    ],
  },
  {
    id: 'signing', title: 'Signing', count: 2, bulletColor: '#d97706',
    leads: [
      { id: 'k7', addr: '22 Plein · Jacobs', meta: ['Tenant signed', 'Owner pending'], action: 'Remind owner', actionTone: 'warn' },
    ],
  },
  {
    id: 'active', title: 'Active', count: 128, bulletColor: '#0d9488',
    leads: [
      { id: 'k8', addr: '128 leases · 8 suburbs', meta: ['R 1.42m MTD'], action: 'See all',  actionTone: 'neutral' },
    ],
  },
  {
    id: 'renewal', title: 'Renewal', count: 5, bulletColor: '#2563eb',
    leads: [
      { id: 'k9',  addr: '4 Church · Mthembu',  meta: ['60d out', 'Escalation 8%'], action: 'Prepare renewal', actionTone: 'warn' },
      { id: 'k10', addr: '19 Main · Pienaar',   meta: ['90d out', 'Escalation 10%'], action: 'Draft', actionTone: 'neutral' },
    ],
  },
  {
    id: 'moveout', title: 'Move-out', count: 2, bulletColor: '#7C3AED',
    leads: [
      { id: 'k11', addr: '3 Dorp · Pienaar', meta: ['Keys back', 'Day 14/21'], action: 'Deduction stmt', actionTone: 'warn' },
    ],
  },
  {
    id: 'refund', title: 'Refund', count: 3, bulletColor: '#dc2626',
    leads: [
      { id: 'k12', addr: '25 Bird · Smit',  meta: ['Day 7/21', 'R 0 deductions'], action: 'Release', actionTone: 'ok' },
    ],
  },
]

const STUB_UPCOMING: UpcomingDay[] = [
  {
    day: 'Today · Thu 18 Apr',
    rows: [
      { time: '09:00', title: 'Ingoing · 22 Plein',           ctx: 'Jacobs family · agent Sarah N.',  icon: 'ClipboardList' },
      { time: '11:00', title: 'Maintenance · 15 Andringa',    ctx: 'EZ Locksmith · door lock · tenant on site', icon: 'Wrench' },
      { time: '14:00', title: 'Mid-tenancy · 4 Church',       ctx: 'Condition check · Mthembu',       icon: 'ClipboardCheck' },
      { time: '16:00', title: 'Gate 3 SLA breach imminent',   ctx: '22 Plein geyser · owner silent 25h', icon: 'ShieldAlert' },
    ],
  },
  {
    day: 'Fri 19 Apr',
    rows: [
      { time: '09:00', title: 'Maintenance · 7A Paul Kruger', ctx: 'BluWater · pool pump',            icon: 'Wrench' },
      { time: '10:00', title: 'Mid-tenancy · 4 Church',       ctx: 'Condition check',                  icon: 'ClipboardCheck' },
      { time: '11:00', title: 'Signing window closes',        ctx: '22 Plein · notify owner',          icon: 'PenTool' },
    ],
  },
  {
    day: 'Sat 20 Apr',
    rows: [
      { time: '10:00', title: 'Maintenance · 33 Ryneveld',    ctx: 'Quick Fix · paint · vacant property', icon: 'Wrench' },
      { time: '11:00', title: 'Viewing · 33 Ryneveld',        ctx: '3 applicants booked',             icon: 'Users' },
    ],
  },
  {
    day: 'Mon 22 Apr',
    rows: [
      { time: '08:00', title: 'Maintenance · Unit 12 WE',     ctx: 'SparkWise · DB board · power off 2h', icon: 'Zap' },
      { time: '—',     title: 'Rent run',                     ctx: '128 leases · statements + reminders', icon: 'Receipt' },
    ],
  },
]

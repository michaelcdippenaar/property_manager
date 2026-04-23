<!--
  AgentPropertiesView — Portfolio list (1:1 port)

  Ported from docs/prototypes/admin-shell/index.html #route-properties.
  Uses .agent-shell scoped CSS inherited from AgentPreviewLayout.
  Clicking a row navigates to /agent/property (god view).
-->
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Filter, Download, Plus } from 'lucide-vue-next'

const router = useRouter()

type StateKey = 'active' | 'signing' | 'vacant' | 'marketing' | 'renewal' | 'moveout' | 'refund'

interface Row {
  addr: string
  extra: string
  type: string
  state: StateKey
  stateLabel: string
  tenant: string
  tenantMuted?: boolean
  rent: string
  next: string
  nextTone?: 'warn' | 'danger' | 'muted' | 'normal'
  nextBold?: boolean
  agent: string
  goto?: string
}

const rows: Row[] = [
  { addr: '15 Andringa, Stellenbosch', extra: 'Erf 1420', type: 'House · 3 bed',
    state: 'active', stateLabel: 'Active',
    tenant: 'Vink family', rent: 'R 15 200',
    next: 'Statement 30 Apr', nextTone: 'muted',
    agent: 'Sarah N.', goto: 'property' },
  { addr: '22 Plein, Stellenbosch', extra: 'Unit 4A', type: 'Apartment · 2 bed',
    state: 'signing', stateLabel: 'Signing',
    tenant: 'Jacobs, K.', rent: 'R 13 500',
    next: 'Owner countersign · SLA 18h', nextTone: 'warn', nextBold: true,
    agent: 'Sarah N.' },
  { addr: '12 Dorp, Stellenbosch', extra: 'Erf 892', type: 'House · 2 bed',
    state: 'vacant', stateLabel: 'Vacant',
    tenant: '—', tenantMuted: true, rent: 'R 12 500',
    next: 'Vacant 12d · list for marketing', nextTone: 'warn', nextBold: true,
    agent: 'Sarah N.' },
  { addr: '33 Ryneveld, Stellenbosch', extra: 'Erf 1701', type: 'Cottage · 2 bed',
    state: 'marketing', stateLabel: 'Marketing',
    tenant: '3 applications', tenantMuted: true, rent: 'R 14 000',
    next: 'Review applications',
    agent: 'Dan T.' },
  { addr: '4 Church, Franschhoek', extra: 'Erf 205', type: 'Cottage · 3 bed',
    state: 'active', stateLabel: 'Active',
    tenant: 'Abrahams family', rent: 'R 18 750',
    next: 'Rent 3d late', nextTone: 'danger', nextBold: true,
    agent: 'Dan T.' },
  { addr: '19 Main, Stellenbosch', extra: 'Unit 2', type: 'Apartment · 1 bed',
    state: 'renewal', stateLabel: 'Renewal due',
    tenant: 'Mthembu, L.', rent: 'R 9 800',
    next: 'Send offer (T-60)',
    agent: 'Sarah N.' },
  { addr: '25 Bird, Stellenbosch', extra: 'Erf 1180', type: 'House · 3 bed',
    state: 'moveout', stateLabel: 'Move-out',
    tenant: 'Smit, R.', rent: 'R 16 900',
    next: 'Book outgoing inspection',
    agent: 'Dan T.' },
  { addr: '3 Dorp, Stellenbosch', extra: 'Erf 54', type: 'Cottage · 2 bed',
    state: 'refund', stateLabel: 'Refund',
    tenant: 'Previously: Pienaar', tenantMuted: true, rent: 'R 13 200',
    next: '14 days to refund · Gate 6', nextTone: 'danger', nextBold: true,
    agent: 'Sarah N.' },
]

function bulletColor(s: StateKey): string {
  switch (s) {
    case 'active':    return 'var(--ok)'
    case 'signing':   return 'var(--warn)'
    case 'vacant':    return 'var(--muted-2)'
    case 'marketing': return 'var(--info)'
    case 'renewal':   return '#D97706'
    case 'moveout':   return 'var(--accent)'
    case 'refund':    return 'var(--danger)'
  }
}

function badgeClass(s: StateKey): string {
  if (s === 'moveout') return 'badge'
  return `badge ${s}`
}

function badgeStyle(s: StateKey): Record<string, string> {
  if (s === 'moveout') return { background: 'var(--accent-soft)', color: 'var(--accent)' }
  return {}
}

function nextStyle(tone?: Row['nextTone']): Record<string, string> {
  if (tone === 'warn')   return { color: 'var(--warn)' }
  if (tone === 'danger') return { color: 'var(--danger)' }
  return {}
}

function goto(r: Row) {
  if (r.goto === 'property') router.push('/agent/property')
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Properties</span></div>
      <div class="page-header-row">
        <div>
          <h1>Portfolio</h1>
          <p class="sub">47 properties · filter by state, agent, suburb, owner</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Filter"><Filter :size="14" />Filter</button>
          <button class="btn" aria-label="Export"><Download :size="14" />Export</button>
          <button class="btn primary" aria-label="Add property"><Plus :size="14" />Add property</button>
        </div>
      </div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th scope="col">Address</th><th scope="col">Type</th><th scope="col">State</th><th scope="col">Tenant</th><th scope="col">Rent</th><th scope="col">Next action</th><th scope="col">Agent</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.addr"
            :style="r.goto === 'property' ? 'cursor:pointer' : ''"
            @click="goto(r)"
          >
            <td>
              <strong>{{ r.addr }}</strong>
              <div class="muted">{{ r.extra }}</div>
            </td>
            <td>{{ r.type }}</td>
            <td>
              <span :class="badgeClass(r.state)" :style="badgeStyle(r.state)">
                <span class="bullet" :style="`background:${bulletColor(r.state)}`" />
                {{ r.stateLabel }}
              </span>
            </td>
            <td :class="r.tenantMuted ? 'muted' : ''">{{ r.tenant }}</td>
            <td class="money">{{ r.rent }}</td>
            <td :class="r.nextTone === 'muted' ? 'muted' : ''">
              <strong v-if="r.nextBold" :style="nextStyle(r.nextTone)">{{ r.next }}</strong>
              <template v-else>{{ r.next }}</template>
            </td>
            <td>{{ r.agent }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

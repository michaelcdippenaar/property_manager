<!--
  AgentSalesView — Real Estate (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-sales.
-->
<script setup lang="ts">
import { ToggleRight, Plus } from 'lucide-vue-next'

type Stage = 'suspensive' | 'negotiating' | 'marketing' | 'transfer'

interface Row {
  property: string
  sub: string
  owner: string
  list: string
  offers: string
  offersMuted?: boolean
  stage: Stage
  stageLabel: string
  conveyancer: string
  conveyancerMuted?: boolean
}

const rows: Row[] = [
  { property: 'Erf 1042, Paarl', sub: '4 bed · 340m²', owner: 'Basson Trust',
    list: 'R 6 850 000', offers: '1 accepted',
    stage: 'suspensive', stageLabel: 'Offer signed · suspensive',
    conveyancer: 'Faber Inc.' },
  { property: '12 Berg, Stellenbosch', sub: '3 bed · 210m²', owner: 'Nkosi family',
    list: 'R 4 200 000', offers: '2 live',
    stage: 'negotiating', stageLabel: 'Negotiating',
    conveyancer: '—', conveyancerMuted: true },
  { property: 'Unit 3, Winelands Estate', sub: 'Sectional title · 98m²', owner: 'Smit, R.',
    list: 'R 2 150 000', offers: '0', offersMuted: true,
    stage: 'marketing', stageLabel: 'Marketing · 14d',
    conveyancer: '—', conveyancerMuted: true },
  { property: 'Erf 702, Franschhoek', sub: 'Vacant land · 812m²', owner: 'Le Roux',
    list: 'R 1 800 000', offers: '1 signed',
    stage: 'transfer', stageLabel: 'In transfer · day 62',
    conveyancer: 'Cilliers Attorneys' },
]

function stageClass(s: Stage) {
  if (s === 'suspensive') return 'badge signing'
  if (s === 'negotiating') return 'badge marketing'
  if (s === 'marketing') return 'badge marketing'
  return 'badge active'
}
function stageBullet(s: Stage) {
  if (s === 'suspensive') return 'var(--warn)'
  if (s === 'negotiating') return 'var(--info)'
  if (s === 'marketing') return 'var(--info)'
  return 'var(--ok)'
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Real Estate</span></div>
      <div class="page-header-row">
        <div>
          <h1>Real Estate</h1>
          <p class="sub">Sales mandates · buyer CRM · offer-to-transfer. Separate product line, same Vault33.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Switch to Rentals"><ToggleRight :size="14" />Switch to Rentals</button>
          <button class="btn primary" aria-label="New mandate"><Plus :size="14" />New mandate</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Sales mandates</div><div class="value">8</div><div class="delta">2 new this month</div></div>
      <div class="stat"><div class="label">Under offer</div><div class="value">3</div><div class="delta">R 14.2m aggregate</div></div>
      <div class="stat"><div class="label">In transfer</div><div class="value">2</div><div class="delta">avg 87d to register</div></div>
      <div class="stat"><div class="label">Commission pipeline</div><div class="value">R 512k</div><div class="delta">next 90 days</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr><th scope="col">Property</th><th scope="col">Owner</th><th scope="col">List price</th><th scope="col">Offers</th><th scope="col">Stage</th><th scope="col">Conveyancer</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.property">
            <td><strong>{{ r.property }}</strong><div class="muted">{{ r.sub }}</div></td>
            <td>{{ r.owner }}</td>
            <td class="money">{{ r.list }}</td>
            <td :class="r.offersMuted ? 'muted' : ''">{{ r.offers }}</td>
            <td>
              <span :class="stageClass(r.stage)">
                <span class="bullet" :style="`background:${stageBullet(r.stage)}`" />
                {{ r.stageLabel }}
              </span>
            </td>
            <td :class="r.conveyancerMuted ? 'muted' : ''">{{ r.conveyancer }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

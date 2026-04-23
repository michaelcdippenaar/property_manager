<!--
  AgentInspectionsView — Inspections list (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-inspections.
-->
<script setup lang="ts">
import { Calendar, Plus } from 'lucide-vue-next'

type InspectionType = 'ingoing' | 'outgoing' | 'mid'
type InspectionStatus = 'scheduled' | 'signed-clean' | 'damage'

interface Row {
  when: string
  whenBold?: boolean
  property: string
  type: InspectionType
  typeLabel: string
  party: string
  agent: string
  status: InspectionStatus
  statusLabel: string
  pdf?: string
}

const rows: Row[] = [
  { when: 'Thu 25 Apr · 11:00', whenBold: true, property: '25 Bird, Stellenbosch',
    type: 'outgoing', typeLabel: 'Outgoing', party: 'Smit, R.', agent: 'Dan T.',
    status: 'scheduled', statusLabel: 'Scheduled' },
  { when: 'Mon 1 May · 09:00', whenBold: true, property: '22 Plein, Stellenbosch',
    type: 'ingoing', typeLabel: 'Ingoing', party: 'Jacobs, K.', agent: 'Sarah N.',
    status: 'scheduled', statusLabel: 'Scheduled' },
  { when: 'Wed 3 May · 14:00', whenBold: true, property: '4 Church, Franschhoek',
    type: 'mid', typeLabel: 'Mid', party: 'Abrahams', agent: 'Dan T.',
    status: 'scheduled', statusLabel: 'Scheduled' },
  { when: 'Wed 8 May · 10:00', whenBold: true, property: '19 Main, Stellenbosch',
    type: 'ingoing', typeLabel: 'Ingoing', party: 'Mthembu (renewal)', agent: 'Sarah N.',
    status: 'scheduled', statusLabel: 'Scheduled' },
  { when: '15 Mar · 09:00', property: '15 Andringa, Stellenbosch',
    type: 'ingoing', typeLabel: 'Ingoing', party: 'Vink family', agent: 'Sarah N.',
    status: 'signed-clean', statusLabel: 'Signed · clean', pdf: 'ingoing.pdf' },
  { when: '8 Apr · 14:00', property: '3 Dorp, Stellenbosch',
    type: 'outgoing', typeLabel: 'Outgoing', party: 'Pienaar (prev)', agent: 'Sarah N.',
    status: 'damage', statusLabel: '3 damage items', pdf: 'outgoing.pdf' },
]

function typeBadgeClass(t: InspectionType) {
  if (t === 'ingoing') return 'badge active'
  if (t === 'mid') return 'badge marketing'
  return 'badge'
}
function typeBadgeStyle(t: InspectionType) {
  if (t === 'outgoing') return 'background:var(--accent-soft);color:var(--accent)'
  return ''
}
function typeBullet(t: InspectionType) {
  if (t === 'ingoing') return 'var(--ok)'
  if (t === 'mid') return 'var(--info)'
  return ''
}
function statusBadgeClass(s: InspectionStatus) {
  if (s === 'scheduled') return 'badge signing'
  if (s === 'signed-clean') return 'badge active'
  return 'badge refund'
}
function statusBullet(s: InspectionStatus) {
  if (s === 'scheduled') return 'var(--warn)'
  if (s === 'signed-clean') return 'var(--ok)'
  return 'var(--danger)'
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Inspections</span></div>
      <div class="page-header-row">
        <div>
          <h1>Inspections</h1>
          <p class="sub">Ingoing · outgoing · mid-tenancy — mobile app, co-signed, side-by-side diff.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Calendar view"><Calendar :size="14" />Calendar view</button>
          <button class="btn primary" aria-label="Schedule inspection"><Plus :size="14" />Schedule</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Next 7 days</div><div class="value">4</div><div class="delta">2 ingoing · 1 outgoing · 1 mid</div></div>
      <div class="stat"><div class="label">This month</div><div class="value">11</div><div class="delta">vs 9 last month</div></div>
      <div class="stat"><div class="label">Avg turnaround</div><div class="value">2.3d</div><div class="delta">outgoing → refund path</div></div>
      <div class="stat"><div class="label">Completion rate</div><div class="value">98%</div><div class="delta">1 rescheduled this month</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr><th scope="col">When</th><th scope="col">Property</th><th scope="col">Type</th><th scope="col">Party</th><th scope="col">Agent</th><th scope="col">Status</th><th scope="col">PDF</th></tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i">
            <td><strong v-if="r.whenBold">{{ r.when }}</strong><template v-else>{{ r.when }}</template></td>
            <td>{{ r.property }}</td>
            <td>
              <span :class="typeBadgeClass(r.type)" :style="typeBadgeStyle(r.type)">
                <span v-if="typeBullet(r.type)" class="bullet" :style="`background:${typeBullet(r.type)}`" />
                {{ r.typeLabel }}
              </span>
            </td>
            <td>{{ r.party }}</td>
            <td>{{ r.agent }}</td>
            <td>
              <span :class="statusBadgeClass(r.status)">
                <span class="bullet" :style="`background:${statusBullet(r.status)}`" />
                {{ r.statusLabel }}
              </span>
            </td>
            <td :class="r.pdf ? '' : 'muted'">
              <a v-if="r.pdf" href="#" style="color:var(--navy)">{{ r.pdf }}</a>
              <template v-else>—</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

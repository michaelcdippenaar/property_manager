<!--
  AgentLeasesView — Leases list (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-leases.
-->
<script setup lang="ts">
import { FileSearch, Plus, Clock, ArrowRight } from 'lucide-vue-next'

interface LeaseRow {
  property: string
  tenant: string
  start: string
  end: string
  rent: string
  status: 'executed' | 'signing' | 'renewal'
  statusLabel: string
  signed: string
}

const rows: LeaseRow[] = [
  { property: '22 Plein, Stellenbosch', tenant: 'Jacobs, K.', start: '1 May 2026', end: '30 Apr 2027',
    rent: 'R 13 500', status: 'signing', statusLabel: 'Countersign pending', signed: 'Tenant ✓ · Owner ⏳' },
  { property: '15 Andringa, Stellenbosch', tenant: 'Vink family', start: '1 Mar 2026', end: '28 Feb 2027',
    rent: 'R 15 200', status: 'executed', statusLabel: 'Executed', signed: 'All parties ✓' },
  { property: '4 Church, Franschhoek', tenant: 'Abrahams family', start: '1 Sep 2025', end: '31 Aug 2026',
    rent: 'R 18 750', status: 'executed', statusLabel: 'Executed', signed: 'All parties ✓' },
  { property: '19 Main, Stellenbosch', tenant: 'Mthembu, L.', start: '1 Jul 2025', end: '30 Jun 2026',
    rent: 'R 9 800', status: 'renewal', statusLabel: 'Renewal due', signed: 'All parties ✓' },
]

function statusClass(s: LeaseRow['status']) {
  if (s === 'executed') return 'badge active'
  if (s === 'signing') return 'badge signing'
  return 'badge renewal'
}
function statusBullet(s: LeaseRow['status']) {
  if (s === 'executed') return 'var(--ok)'
  if (s === 'signing') return 'var(--warn)'
  return '#D97706'
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Leases</span></div>
      <div class="page-header-row">
        <div>
          <h1>Leases</h1>
          <p class="sub">38 active · 2 in signing · 1 awaiting countersign</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Templates"><FileSearch :size="14" />Templates</button>
          <button class="btn primary" aria-label="New lease"><Plus :size="14" />New lease</button>
        </div>
      </div>
    </div>

    <div class="alert-strip">
      <Clock :size="14" />
      <strong>1 lease awaiting owner countersign · 22 Plein · SLA breaches in 18h</strong>
      <button class="btn ghost" style="margin-left:auto" aria-label="Go to gate"><ArrowRight :size="14" />Go to gate</button>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th scope="col">Property</th><th scope="col">Tenant</th><th scope="col">Start</th><th scope="col">End</th><th scope="col">Rent</th><th scope="col">Status</th><th scope="col">Signed</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.property">
            <td><strong>{{ r.property }}</strong></td>
            <td>{{ r.tenant }}</td>
            <td>{{ r.start }}</td>
            <td>{{ r.end }}</td>
            <td class="money">{{ r.rent }}</td>
            <td>
              <span :class="statusClass(r.status)">
                <span class="bullet" :style="`background:${statusBullet(r.status)}`" />
                {{ r.statusLabel }}
              </span>
            </td>
            <td>{{ r.signed }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<!--
  AgentDepositsView — Trust account (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-deposits.
-->
<script setup lang="ts">
import { RefreshCw, Download } from 'lucide-vue-next'

interface Row {
  property: string
  tenant: string
  principal: string
  interest: string
  status: 'refund' | 'held'
  statusLabel: string
  refundBy: string
  refundBold?: boolean
}

const rows: Row[] = [
  { property: '3 Dorp, Stellenbosch', tenant: 'Pienaar (outgoing)', principal: 'R 24 000', interest: 'R 842',
    status: 'refund', statusLabel: 'Refund · Gate 6', refundBy: '14 days', refundBold: true },
  { property: '15 Andringa, Stellenbosch', tenant: 'Vink family', principal: 'R 30 400', interest: 'R 612',
    status: 'held', statusLabel: 'Held', refundBy: '28 Feb 2027' },
  { property: '4 Church, Franschhoek', tenant: 'Abrahams family', principal: 'R 37 500', interest: 'R 1 205',
    status: 'held', statusLabel: 'Held', refundBy: '31 Aug 2026' },
]
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Deposits</span></div>
      <div class="page-header-row">
        <div>
          <h1>Trust account</h1>
          <p class="sub">Separate interest-bearing account · ABSA-4412 · R 892 450 held across 38 leases</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Reconcile"><RefreshCw :size="14" />Reconcile</button>
          <button class="btn" aria-label="Download statement"><Download :size="14" />Statement</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Total held</div><div class="value">R 892 450</div><div class="delta">across 38 leases</div></div>
      <div class="stat"><div class="label">Interest accrued YTD</div><div class="value">R 18 740</div><div class="delta">Pro-rata to tenants</div></div>
      <div class="stat"><div class="label">Pending refunds</div><div class="value">1</div><div class="delta down">3 Dorp · 14d left</div></div>
      <div class="stat"><div class="label">Disputed</div><div class="value">0</div><div class="delta">—</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr><th scope="col">Property</th><th scope="col">Tenant</th><th scope="col">Principal</th><th scope="col">Interest</th><th scope="col">Status</th><th scope="col">Refund by</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.property">
            <td><strong>{{ r.property }}</strong></td>
            <td>{{ r.tenant }}</td>
            <td class="money">{{ r.principal }}</td>
            <td class="money">{{ r.interest }}</td>
            <td>
              <span :class="r.status === 'refund' ? 'badge refund' : 'badge active'">
                <span
                  class="bullet"
                  :style="`background:${r.status === 'refund' ? 'var(--danger)' : 'var(--ok)'}`"
                />
                {{ r.statusLabel }}
              </span>
            </td>
            <td :class="r.refundBold ? '' : 'muted'">
              <strong v-if="r.refundBold" style="color:var(--danger)">{{ r.refundBy }}</strong>
              <template v-else>{{ r.refundBy }}</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

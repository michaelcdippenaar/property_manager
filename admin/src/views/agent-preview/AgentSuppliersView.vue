<!--
  AgentSuppliersView — Supplier panel (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-suppliers.
-->
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Filter, MapPin, Plus, CheckCircle2, AlertCircle, Info } from 'lucide-vue-next'

const router = useRouter()

interface Row {
  name: string
  sub: string
  categories: string
  area: string
  rating: string
  ratingCount: string
  jobs: number
  open: number
  fica: 'ok' | 'warn'
  rate: string
}

const rows: Row[] = [
  { name: 'SAPlumb (Pty) Ltd', sub: 'VAT 4150228812',
    categories: 'Plumbing · Geyser', area: 'Stellenbosch · Somerset W.',
    rating: '4.6★', ratingCount: '(47)', jobs: 47, open: 2, fica: 'ok', rate: 'R 220/hr' },
  { name: 'EZ Locksmith (Pty) Ltd', sub: 'VAT 4150119283',
    categories: 'Locks · Security', area: 'Winelands-wide',
    rating: '4.8★', ratingCount: '(14)', jobs: 14, open: 1, fica: 'ok', rate: 'R 380 call-out' },
  { name: 'Kaap Damp Solutions', sub: 'CC 2020/4456/07',
    categories: 'Damp · Roofing', area: 'Stellenbosch · Paarl',
    rating: '4.3★', ratingCount: '(8)', jobs: 8, open: 1, fica: 'warn', rate: 'Quote per job' },
  { name: 'Quick Fix Co.', sub: 'Sole prop · J. Moodley',
    categories: 'Handyman · Paint · Minor electrical', area: 'Stellenbosch',
    rating: '4.7★', ratingCount: '(22)', jobs: 22, open: 1, fica: 'ok', rate: 'R 180/hr' },
  { name: 'SparkWise Electrical', sub: 'VAT 4150338271',
    categories: 'Electrical · CoC · DB board', area: 'Winelands · Helderberg',
    rating: '4.5★', ratingCount: '(11)', jobs: 11, open: 1, fica: 'ok', rate: 'R 280/hr + CoC' },
  { name: 'BluWater Pool Services', sub: 'VAT 4150442166',
    categories: 'Pool · Irrigation', area: 'Stellenbosch · Paarl',
    rating: '4.6★', ratingCount: '(6)', jobs: 6, open: 1, fica: 'ok', rate: 'R 450/visit' },
  { name: 'Winelands Pest', sub: 'VAT 4150776221',
    categories: 'Pest · Fumigation', area: 'Winelands-wide',
    rating: '4.4★', ratingCount: '(5)', jobs: 5, open: 0, fica: 'ok', rate: 'R 650 standard' },
  { name: 'GreenTouch Gardens', sub: 'Sole prop · T. Ndlovu',
    categories: 'Garden · Lawn', area: 'Stellenbosch',
    rating: '4.9★', ratingCount: '(18)', jobs: 18, open: 0, fica: 'ok', rate: 'R 380/visit' },
]
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb">
        <a @click.prevent="router.push('/agent/maintenance')" href="#">Maintenance</a>
        · <span>Suppliers</span>
      </div>
      <div class="page-header-row">
        <div>
          <h1>Supplier panel</h1>
          <p class="sub">14 active suppliers · rolling 6-month ratings · FICA + banking on file in Vault33.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Filter by category"><Filter :size="14" />Category</button>
          <button class="btn" aria-label="Filter by area"><MapPin :size="14" />Area</button>
          <button class="btn primary" aria-label="Invite supplier"><Plus :size="14" />Invite supplier</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Active suppliers</div><div class="value">14</div><div class="delta">+1 this quarter</div></div>
      <div class="stat"><div class="label">Avg rating</div><div class="value">4.6★</div><div class="delta">across 89 jobs</div></div>
      <div class="stat"><div class="label">Spend YTD</div><div class="value">R 38 420</div><div class="delta">via supplier panel</div></div>
      <div class="stat"><div class="label">FICA gaps</div><div class="value" style="color:var(--warn)">1</div><div class="delta down">Kaap Damp · missing CIPC</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr><th scope="col">Supplier</th><th scope="col">Categories</th><th scope="col">Area</th><th scope="col">Rating</th><th scope="col">Jobs</th><th scope="col">Open</th><th scope="col">FICA</th><th scope="col">Rate</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.name">
            <td><strong>{{ r.name }}</strong><div class="muted">{{ r.sub }}</div></td>
            <td>{{ r.categories }}</td>
            <td>{{ r.area }}</td>
            <td><strong>{{ r.rating }}</strong> <span class="muted">{{ r.ratingCount }}</span></td>
            <td>{{ r.jobs }}</td>
            <td>{{ r.open }}</td>
            <td>
              <span
                style="display:inline-flex;align-items:center;gap:4px;font-size:12px"
                :style="`color:${r.fica === 'ok' ? 'var(--ok)' : 'var(--warn)'}`"
                :aria-label="`FICA: ${r.fica === 'ok' ? 'Verified' : 'Missing'}`"
              >
                <CheckCircle2 v-if="r.fica === 'ok'" :size="13" />
                <AlertCircle v-else :size="13" />
                <span>{{ r.fica === 'ok' ? 'Verified' : 'Missing' }}</span>
              </span>
            </td>
            <td class="money">{{ r.rate }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div style="padding:0 32px 40px">
      <div class="pcard">
        <h3><Info :size="14" />Routing rules</h3>
        <div style="font-size:13px;margin-top:10px">
          <p><strong>Default pick:</strong> highest rating within category + area, after filtering out any supplier with open dispute or FICA gap.</p>
          <p><strong>Competitive quotes:</strong> agent can request 3 quotes if job estimate &gt; R 15 000 (system auto-invites top 3 in category).</p>
          <p><strong>Auto-demote:</strong> 6-month rolling rating &lt; 3.5 → supplier dropped from routing pool, flagged for review.</p>
          <p><strong>Owner preferred:</strong> owner can nominate a specific supplier in their mandate — that supplier always routed first regardless of rating.</p>
          <p><strong>FICA gap:</strong> supplier can still quote but payment blocked until FICA complete.</p>
        </div>
      </div>
    </div>
  </section>
</template>

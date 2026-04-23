<!--
  AgentBiView — Business Intelligence (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-bi.
-->
<script setup lang="ts">
import { Calendar, Download, MapPin, AlertCircle, TrendingUp } from 'lucide-vue-next'

interface Bar {
  label: string
  height: number
  current?: boolean
  title?: string
}

const bars: Bar[] = [
  { label: 'May', height: 40, title: 'May R 98k' },
  { label: 'Jun', height: 52 },
  { label: 'Jul', height: 58 },
  { label: 'Aug', height: 61 },
  { label: 'Sep', height: 67 },
  { label: 'Oct', height: 72 },
  { label: 'Nov', height: 74 },
  { label: 'Dec', height: 78 },
  { label: 'Jan', height: 81 },
  { label: 'Feb', height: 84 },
  { label: 'Mar', height: 88 },
  { label: 'Apr', height: 95, current: true, title: 'Apr R 142.8k' },
]

interface Vacancy { suburb: string; value: string }
const vacancy: Vacancy[] = [
  { suburb: 'Stellenbosch', value: '2 / 28 · 7.1%' },
  { suburb: 'Paarl', value: '1 / 9 · 11.1%' },
  { suburb: 'Franschhoek', value: '1 / 5 · 20.0%' },
  { suburb: 'Somerset West', value: '1 / 5 · 20.0%' },
]

interface Aging { n: number; label: string; color: string }
const aging: Aging[] = [
  { n: 35, label: 'Paid on time', color: 'var(--ok)' },
  { n: 2, label: '1–7 days late', color: 'var(--warn)' },
  { n: 1, label: '8–14 days', color: 'var(--warn)' },
  { n: 0, label: '15–30 days', color: 'var(--danger)' },
  { n: 0, label: '30+ days (notice)', color: 'var(--danger)' },
]
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Business Intelligence</span></div>
      <div class="page-header-row">
        <div>
          <h1>Business intelligence</h1>
          <p class="sub">Commission trends · vacancy · arrears · cohort retention. Metabase-embedded + Klikk native views.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Last 90 days"><Calendar :size="14" />Last 90d</button>
          <button class="btn" aria-label="Export"><Download :size="14" />Export</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Commission MTD</div><div class="value">R 142 800</div><div class="delta">+8.3% vs last month</div></div>
      <div class="stat"><div class="label">Portfolio GMV</div><div class="value">R 612k</div><div class="delta">rent collected monthly</div></div>
      <div class="stat"><div class="label">Occupancy</div><div class="value">89.4%</div><div class="delta">42 of 47 properties</div></div>
      <div class="stat"><div class="label">Avg days vacant</div><div class="value">18</div><div class="delta down">vs Stellenbosch median 14d</div></div>
    </div>

    <div class="bi-grid">
      <div class="pcard">
        <h3><TrendingUp :size="14" />Commission — 12 months</h3>
        <div class="bi-bars">
          <div
            v-for="b in bars"
            :key="b.label"
            :style="`background:${b.current ? 'var(--navy)' : 'var(--navy-soft)'};height:${b.height}%;border-radius:4px 4px 0 0`"
            :title="b.title"
          />
        </div>
        <div class="bi-bar-labels">
          <template v-for="b in bars" :key="b.label">
            <strong v-if="b.current" style="color:var(--navy)">{{ b.label }}</strong>
            <span v-else>{{ b.label }}</span>
          </template>
        </div>
      </div>
      <div class="pcard">
        <h3><MapPin :size="14" />Vacancy by suburb</h3>
        <div style="font-size:13px">
          <div v-for="(v, i) in vacancy" :key="v.suburb" class="bi-vac-row" :class="{ last: i === vacancy.length - 1 }">
            <span>{{ v.suburb }}</span>
            <strong>{{ v.value }}</strong>
          </div>
        </div>
      </div>
    </div>

    <div class="bi-arrears-wrap">
      <div class="pcard">
        <h3><AlertCircle :size="14" />Arrears aging</h3>
        <div class="bi-arrears-grid">
          <div v-for="a in aging" :key="a.label" class="bi-arrears-cell">
            <div :style="`font-family:'Fraunces',serif;font-size:22px;color:${a.color};font-weight:600`">{{ a.n }}</div>
            <div style="font-size:11px;color:var(--muted)">{{ a.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style>
.agent-shell .bi-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  padding: 0 32px 20px;
}
.agent-shell .bi-bars {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 4px;
  height: 180px;
  align-items: end;
  margin: 14px 0 6px;
}
.agent-shell .bi-bar-labels {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 4px;
  font-size: 10px;
  color: var(--muted);
  font-family: 'JetBrains Mono', monospace;
  text-align: center;
}
.agent-shell .bi-vac-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}
.agent-shell .bi-vac-row.last { border-bottom: none; }
.agent-shell .bi-arrears-wrap {
  padding: 0 32px 40px;
}
.agent-shell .bi-arrears-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-top: 10px;
}
.agent-shell .bi-arrears-cell {
  background: var(--paper);
  padding: 14px;
  border-radius: 10px;
  text-align: center;
}
</style>

<!--
  AgentMaintenanceView — Work orders kanban (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-maintenance.
-->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Users,
  Download,
  Plus,
  ShieldCheck,
  ArrowRight,
  LayoutGrid,
  List,
  Calendar,
  Filter,
  MapPin,
  Search,
  Check,
  Wrench,
  Mail,
  Truck,
  Receipt,
  Clock,
} from 'lucide-vue-next'

const router = useRouter()
const view = ref<'kanban' | 'table' | 'calendar'>('kanban')

function goTicket() {
  router.push('/agent/maintenance-ticket')
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Maintenance</span></div>
      <div class="page-header-row">
        <div>
          <h1>Work orders</h1>
          <p class="sub">12 open · 1 awaiting owner approval · 1 supplier en route · R 38 420 spend YTD</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="View suppliers" @click="router.push('/agent/suppliers')"><Users :size="14" />Suppliers</button>
          <button class="btn" aria-label="Export"><Download :size="14" />Export</button>
          <button class="btn primary" aria-label="New ticket"><Plus :size="14" />New ticket</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Open tickets</div><div class="value">12</div><div class="delta">4 new · 3 quoted · 2 dispatched · 2 in progress · 1 done</div></div>
      <div class="stat"><div class="label">Gate 3 waiting</div><div class="value" style="color:var(--warn)">1</div><div class="delta down">22 Plein · Geyser · owner silent 25h</div></div>
      <div class="stat"><div class="label">Avg close time</div><div class="value">4.2d</div><div class="delta">within SLA</div></div>
      <div class="stat"><div class="label">Spend MTD</div><div class="value">R 8 240</div><div class="delta">from trust · 6 invoices</div></div>
    </div>

    <div class="alert-strip">
      <ShieldCheck :size="14" />
      <strong>1 Gate 3 awaiting owner decision</strong> · 22 Plein geyser · R 8 200 · quote received 25h ago · SLA breach in 23h
      <button class="btn ghost" style="margin-left:auto" aria-label="Review and chase" @click="goTicket"><ArrowRight :size="14" />Review &amp; chase</button>
    </div>

    <!-- View toolbar -->
    <div style="padding:20px 32px 12px;display:flex;align-items:center;gap:14px;border-bottom:1px solid var(--line)">
      <div class="view-toggle" style="margin-left:0">
        <button :class="view === 'kanban'   ? 'active' : ''" @click="view = 'kanban'"><LayoutGrid :size="13" />Kanban</button>
        <button :class="view === 'table'    ? 'active' : ''" @click="view = 'table'"><List :size="13" />Table</button>
        <button :class="view === 'calendar' ? 'active' : ''" @click="view = 'calendar'"><Calendar :size="13" />Calendar</button>
      </div>
      <button class="btn" aria-label="Filter by category"><Filter :size="14" />All categories</button>
      <button class="btn" aria-label="Filter by suburb"><MapPin :size="14" />All suburbs</button>
      <button class="btn" aria-label="Filter by supplier"><Users :size="14" />All suppliers</button>
      <div class="search" style="flex:1;max-width:none">
        <Search :size="16" />
        <input placeholder="Search tickets by property, issue, supplier…" />
      </div>
    </div>

    <!-- Kanban -->
    <div v-if="view === 'kanban'" class="view-pane active">
      <div class="kanban" style="grid-template-columns:repeat(6,minmax(220px,1fr));min-width:1400px;overflow-x:auto">
        <!-- New -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--muted)" />New</div><div class="col-count">4</div></div>
          <div class="card" style="cursor:pointer" @click="goTicket">
            <div class="card-addr">#232 · 12 Dorp</div>
            <div class="card-meta"><span class="tag">Plumbing</span><span class="tag">Low</span><span class="tag muted">2h ago</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Leaking tap in kitchen</div>
            <div class="card-action"><ArrowRight :size="12" />Triage</div>
          </div>
          <div class="card">
            <div class="card-addr">#231 · 4 Church</div>
            <div class="card-meta"><span class="tag">Electrical</span><span class="tag" style="color:var(--warn)">High</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Gate motor not responding</div>
            <div class="card-action"><ArrowRight :size="12" />Request quote</div>
          </div>
          <div class="card">
            <div class="card-addr">#229 · Unit 5 Kloof.</div>
            <div class="card-meta"><span class="tag">Pest</span><span class="tag">Medium</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Rats in ceiling</div>
            <div class="card-action"><ArrowRight :size="12" />Triage</div>
          </div>
          <div class="card">
            <div class="card-addr">#227 · 19 Main</div>
            <div class="card-meta"><span class="tag">Handyman</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Cupboard door off hinges</div>
            <div class="card-action"><ArrowRight :size="12" />Triage</div>
          </div>
        </div>
        <!-- Quoted -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--info)" />Quoted</div><div class="col-count">3</div></div>
          <div class="card" style="border-color:var(--warn);border-width:2px;cursor:pointer" @click="goTicket">
            <div class="card-addr">#230 · 22 Plein</div>
            <div class="card-meta"><span class="tag">Plumbing</span><span class="tag money">R 8 200</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Geyser replacement</div>
            <div class="card-action warn"><ShieldCheck :size="12" />Gate 3 · owner silent 25h</div>
          </div>
          <div class="card">
            <div class="card-addr">#226 · 33 Ryneveld</div>
            <div class="card-meta"><span class="tag">Handyman</span><span class="tag money">R 3 600</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Interior paint touch-up</div>
            <div class="card-action ok"><Check :size="12" />Auto-approved · dispatch</div>
          </div>
          <div class="card">
            <div class="card-addr">#225 · 8 Lourens</div>
            <div class="card-meta"><span class="tag">Roofing</span><span class="tag money">R 4 800</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Gutter cleaning + downpipe</div>
            <div class="card-action"><Mail :size="12" />Sent to owner</div>
          </div>
        </div>
        <!-- Dispatched -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--warn)" />Dispatched</div><div class="col-count">2</div></div>
          <div class="card" style="cursor:pointer" @click="goTicket">
            <div class="card-addr">#228 · 15 Andringa</div>
            <div class="card-meta"><span class="tag">Locks</span><span class="tag">EZ Locksmith</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Door lock failure</div>
            <div class="card-action"><Truck :size="12" />ETA 11:00 today</div>
          </div>
          <div class="card">
            <div class="card-addr">#223 · 7A Paul Kruger</div>
            <div class="card-meta"><span class="tag">Pool</span><span class="tag">BluWater</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Pool pump service</div>
            <div class="card-action"><Truck :size="12" />Tomorrow 09:00</div>
          </div>
        </div>
        <!-- In progress -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--ok)" />In progress</div><div class="col-count">2</div></div>
          <div class="card">
            <div class="card-addr">#220 · 8 Lourens</div>
            <div class="card-meta"><span class="tag">Damp</span><span class="tag">Kaap Damp</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Damp repair — bathroom wall</div>
            <div class="card-action ok"><Wrench :size="12" />Day 2/3 on site</div>
          </div>
          <div class="card">
            <div class="card-addr">#218 · Unit 12 WE</div>
            <div class="card-meta"><span class="tag">Electrical</span><span class="tag">SparkWise</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">DB board upgrade</div>
            <div class="card-action ok"><Wrench :size="12" />Day 1/2</div>
          </div>
        </div>
        <!-- Done · awaiting invoice -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--accent)" />Done · awaiting invoice</div><div class="col-count">1</div></div>
          <div class="card">
            <div class="card-addr">#219 · 15 Andringa</div>
            <div class="card-meta"><span class="tag">Plumbing</span><span class="tag money">R 2 400</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Geyser element</div>
            <div class="card-action"><Receipt :size="12" />Invoice uploaded · pay</div>
          </div>
        </div>
        <!-- Closed -->
        <div class="kcol">
          <div class="col-head"><div class="col-title"><span class="bullet" style="background:var(--navy)" />Closed</div><div class="col-count">27</div></div>
          <div class="card">
            <div class="card-addr">#217 · 4 Church</div>
            <div class="card-meta"><span class="tag money">R 1 850</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Garden service (monthly)</div>
            <div class="card-action ok"><Check :size="12" />Paid · 4.9★</div>
          </div>
          <div class="card">
            <div class="card-addr">#214 · 19 Main</div>
            <div class="card-meta"><span class="tag money">R 780</span></div>
            <div style="font-size:12px;color:var(--muted);margin-bottom:8px">Kitchen tap washer</div>
            <div class="card-action ok"><Check :size="12" />Paid · 5★</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Table view -->
    <div v-if="view === 'table'" class="view-pane active">
      <div class="table-wrap">
        <table class="data">
          <thead>
            <tr>
              <th scope="col">#</th><th scope="col">Property</th><th scope="col">Issue</th><th scope="col">Category</th><th scope="col">Urgency</th>
              <th scope="col">Supplier</th><th scope="col">Amount</th><th scope="col">State</th><th scope="col">Age</th><th scope="col">Bearer</th>
            </tr>
          </thead>
          <tbody>
            <tr style="cursor:pointer" @click="goTicket">
              <td><strong>#232</strong></td><td>12 Dorp, Stellenbosch</td><td>Leaking tap — kitchen</td><td>Plumbing</td>
              <td><span class="badge vacant">Low</span></td>
              <td class="muted">—</td><td class="muted">—</td>
              <td><span class="badge" style="background:var(--line);color:var(--muted)"><span class="bullet" style="background:var(--muted)" />New</span></td>
              <td>2h</td><td>Owner</td>
            </tr>
            <tr>
              <td><strong>#231</strong></td><td>4 Church, Franschhoek</td><td>Gate motor failure</td><td>Electrical</td>
              <td><span class="badge signing">High</span></td>
              <td class="muted">—</td><td class="muted">—</td>
              <td><span class="badge" style="background:var(--line);color:var(--muted)"><span class="bullet" style="background:var(--muted)" />New</span></td>
              <td>5h</td><td>Owner</td>
            </tr>
            <tr style="cursor:pointer" @click="goTicket">
              <td><strong>#230</strong></td><td>22 Plein, Stellenbosch</td><td>Geyser replacement</td><td>Plumbing</td>
              <td><span class="badge signing">High</span></td>
              <td>SAPlumb</td><td class="money">R 8 200</td>
              <td><span class="badge" style="background:#F3E8FF;color:#7C3AED"><span class="bullet" style="background:#7C3AED" />Gate 3</span></td>
              <td>1d 1h</td><td>Owner</td>
            </tr>
            <tr>
              <td><strong>#228</strong></td><td>15 Andringa, Stellenbosch</td><td>Door lock failure</td><td>Locks/security</td>
              <td><span class="badge signing">Medium</span></td>
              <td>EZ Locksmith</td><td class="money">R 1 850</td>
              <td><span class="badge signing"><span class="bullet" style="background:var(--warn)" />Dispatched</span></td>
              <td>1d</td><td>Owner</td>
            </tr>
            <tr>
              <td><strong>#226</strong></td><td>33 Ryneveld, Stellenbosch</td><td>Paint touch-up</td><td>Handyman</td>
              <td><span class="badge vacant">Low</span></td>
              <td>Quick Fix Co.</td><td class="money">R 3 600</td>
              <td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Approved</span></td>
              <td>2d</td><td>Owner</td>
            </tr>
            <tr>
              <td><strong>#220</strong></td><td>8 Lourens, Somerset W.</td><td>Damp repair · bathroom</td><td>Roofing</td>
              <td><span class="badge signing">Medium</span></td>
              <td>Kaap Damp</td><td class="money">R 4 600</td>
              <td><span class="badge active"><span class="bullet" style="background:var(--ok)" />In progress</span></td>
              <td>3d</td><td>Owner</td>
            </tr>
            <tr>
              <td><strong>#219</strong></td><td>15 Andringa, Stellenbosch</td><td>Geyser element</td><td>Plumbing</td>
              <td><span class="badge vacant">Low</span></td>
              <td>SAPlumb</td><td class="money">R 2 400</td>
              <td><span class="badge" style="background:var(--accent-soft);color:var(--accent)"><span class="bullet" style="background:var(--accent)" />Awaiting payment</span></td>
              <td>21d</td><td>Owner</td>
            </tr>
            <tr>
              <td>#218</td><td>Unit 12, Winelands Est.</td><td>DB board upgrade</td><td>Electrical</td>
              <td><span class="badge signing">Medium</span></td>
              <td>SparkWise</td><td class="money">R 6 200</td>
              <td><span class="badge active"><span class="bullet" style="background:var(--ok)" />In progress</span></td>
              <td>2d</td><td>Owner</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Calendar view -->
    <div v-if="view === 'calendar'" class="view-pane active">
      <div class="table-wrap">
        <div class="pcard">
          <h3><Calendar :size="14" />Upcoming supplier visits · next 14 days</h3>
          <div style="font-family:'JetBrains Mono',monospace;font-size:12px;margin-top:12px">
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:140px 1fr auto;gap:14px;align-items:center">
              <strong>Today 11:00</strong>
              <span><strong>EZ Locksmith</strong> · 15 Andringa · door lock #228 · tenant P. Vink on site</span>
              <button class="btn ghost" aria-label="Detail for EZ Locksmith today" @click="goTicket">Detail →</button>
            </div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:140px 1fr auto;gap:14px;align-items:center">
              <strong>Today 14:00</strong>
              <span><strong>Kaap Damp</strong> · 8 Lourens · damp repair #220 · day 2/3 · no tenant access needed</span>
              <button class="btn ghost" aria-label="Detail for Kaap Damp today">Detail →</button>
            </div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:140px 1fr auto;gap:14px;align-items:center">
              <strong>Fri 19 Apr 09:00</strong>
              <span><strong>BluWater Pool</strong> · 7A Paul Kruger · pump service #223 · coordinate key pickup</span>
              <button class="btn ghost" aria-label="Detail for BluWater Pool">Detail →</button>
            </div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:140px 1fr auto;gap:14px;align-items:center">
              <strong>Sat 20 Apr 10:00</strong>
              <span><strong>Quick Fix Co.</strong> · 33 Ryneveld · paint touch-up #226 · vacant property</span>
              <button class="btn ghost" aria-label="Detail for Quick Fix Co.">Detail →</button>
            </div>
            <div style="padding:10px 0;display:grid;grid-template-columns:140px 1fr auto;gap:14px;align-items:center">
              <strong>Mon 22 Apr 08:00</strong>
              <span><strong>SparkWise</strong> · Unit 12 WE · DB board #218 · day 2/2 · power will be off 2h</span>
              <button class="btn ghost" aria-label="Detail for SparkWise">Detail →</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

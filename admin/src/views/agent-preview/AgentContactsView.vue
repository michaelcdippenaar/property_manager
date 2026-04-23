<!--
  AgentContactsView — Contacts / unified CRM (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-contacts.
-->
<script setup lang="ts">
import { Filter, Plus, CheckCircle2, AlertCircle, Clock } from 'lucide-vue-next'

type Role = 'tenant' | 'tenant-pending' | 'owner' | 'supplier' | 'applicant'
type Status = 'ok' | 'warn' | 'pending'

interface Row {
  name: string
  sub: string
  role: Role
  roleLabel: string
  phone: string
  email: string
  popia: Status
  fica: Status
  linked: string
}

const rows: Row[] = [
  { name: 'Piet Vink', sub: 'ID 8603…·Born 1986', role: 'tenant', roleLabel: 'Tenant',
    phone: '082 451 9928', email: 'piet@v…', popia: 'ok', fica: 'ok', linked: '15 Andringa (lease)' },
  { name: 'J. van der Merwe', sub: 'ID 5511…', role: 'owner', roleLabel: 'Owner',
    phone: '083 229 1144', email: 'jvdm@…', popia: 'ok', fica: 'ok', linked: '15 Andringa · 4 Church (2 mandates)' },
  { name: 'EZ Locksmith (Pty) Ltd', sub: '2018/127833/07', role: 'supplier', roleLabel: 'Supplier',
    phone: '021 883 0119', email: 'ops@ez…', popia: 'ok', fica: 'ok', linked: '14 jobs · locks · 4.8★' },
  { name: 'Kaap Damp Solutions', sub: '2020/4456/07', role: 'supplier', roleLabel: 'Supplier',
    phone: '021 776 2002', email: 'work@k…', popia: 'ok', fica: 'warn', linked: '3 jobs · damp/roof · 4.3★' },
  { name: 'K. Jacobs', sub: 'ID 9012…', role: 'tenant-pending', roleLabel: 'Tenant (pending)',
    phone: '084 007 1144', email: 'kj@…', popia: 'ok', fica: 'ok', linked: '22 Plein (lease signing)' },
  { name: 'Applicant · L. Thembi', sub: 'New · 3 days ago', role: 'applicant', roleLabel: 'Applicant',
    phone: '076 228 4471', email: 'lt@…', popia: 'ok', fica: 'pending', linked: '8 Lourens (application)' },
]

function roleClass(r: Role) {
  if (r === 'tenant') return 'badge active'
  if (r === 'owner') return 'badge marketing'
  if (r === 'tenant-pending') return 'badge signing'
  if (r === 'applicant') return 'badge vacant'
  return 'badge'
}
function roleStyle(r: Role) {
  if (r === 'supplier') return 'background:#F3E8FF;color:#7C3AED'
  return ''
}
function roleBullet(r: Role) {
  if (r === 'tenant') return 'var(--ok)'
  if (r === 'owner') return 'var(--info)'
  if (r === 'tenant-pending') return 'var(--warn)'
  if (r === 'applicant') return 'var(--muted-2)'
  if (r === 'supplier') return '#7C3AED'
  return ''
}

interface StatusDisplay { icon: unknown; color: string; label: string }
function statusDisplay(s: Status): StatusDisplay {
  if (s === 'ok')      return { icon: CheckCircle2, color: 'var(--ok)',   label: 'Verified' }
  if (s === 'warn')    return { icon: AlertCircle,  color: 'var(--warn)', label: 'Missing' }
  return                      { icon: Clock,        color: 'var(--muted)', label: 'Pending' }
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Contacts</span></div>
      <div class="page-header-row">
        <div>
          <h1>Contacts</h1>
          <p class="sub">Owners · tenants · suppliers · applicants — unified CRM, one person, one record.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Filter contacts"><Filter :size="14" />Filter</button>
          <button class="btn primary" aria-label="Add contact"><Plus :size="14" />Add contact</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Owners</div><div class="value">47</div><div class="delta">42 with active mandate</div></div>
      <div class="stat"><div class="label">Tenants (active)</div><div class="value">38</div><div class="delta">+3 this quarter</div></div>
      <div class="stat"><div class="label">Suppliers</div><div class="value">14</div><div class="delta">4.6★ avg rating</div></div>
      <div class="stat"><div class="label">Applicants (open)</div><div class="value">11</div><div class="delta">5 screening · 6 viewings</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Role</th>
            <th scope="col">Phone</th>
            <th scope="col">Email</th>
            <th scope="col">POPIA</th>
            <th scope="col">FICA</th>
            <th scope="col">Linked</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.name">
            <td><strong>{{ r.name }}</strong><div class="muted">{{ r.sub }}</div></td>
            <td>
              <span :class="roleClass(r.role)" :style="roleStyle(r.role)">
                <span class="bullet" :style="`background:${roleBullet(r.role)}`" />
                {{ r.roleLabel }}
              </span>
            </td>
            <td>{{ r.phone }}</td>
            <td>{{ r.email }}</td>
            <td>
              <span
                style="display:inline-flex;align-items:center;gap:4px;font-size:12px"
                :style="`color:${statusDisplay(r.popia).color}`"
                :aria-label="`POPIA: ${statusDisplay(r.popia).label}`"
              >
                <component :is="statusDisplay(r.popia).icon" :size="13" />
                <span>{{ statusDisplay(r.popia).label }}</span>
              </span>
            </td>
            <td>
              <span
                style="display:inline-flex;align-items:center;gap:4px;font-size:12px"
                :style="`color:${statusDisplay(r.fica).color}`"
                :aria-label="`FICA: ${statusDisplay(r.fica).label}`"
              >
                <component :is="statusDisplay(r.fica).icon" :size="13" />
                <span>{{ statusDisplay(r.fica).label }}</span>
              </span>
            </td>
            <td>{{ r.linked }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<!--
  AgentVaultView — Vault33 documents (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-documents.
-->
<script setup lang="ts">
import { Download, Upload, ShieldCheck } from 'lucide-vue-next'

interface Row {
  doc: string
  sub: string
  type: string
  linked: string
  added: string
  retention: string
  reads: number
  purge: string
  purgeWarn?: boolean
  purgeHold?: boolean
}

const rows: Row[] = [
  { doc: 'Lease · 15 Andringa (2026-27)', sub: 'sha: a7f2…·3.2 MB',
    type: 'signed_lease', linked: 'Vink family', added: '15 Jan 2026',
    retention: 'rha_lease_5y', reads: 7, purge: '28 Feb 2032' },
  { doc: 'Ingoing inspection · 15 Andringa', sub: '42 photos · signed',
    type: 'inspection', linked: 'Vink family', added: '15 Jan 2026',
    retention: 'inspection_3y', reads: 2, purge: '28 Feb 2030' },
  { doc: 'ID copy · P. Vink', sub: 'PDF · FICA verified',
    type: 'identity', linked: 'Piet Vink', added: '13 Jan 2026',
    retention: 'fica_5y', reads: 3, purge: '13 Jan 2031' },
  { doc: 'Credit report · L. Thembi', sub: 'TransUnion · score 712',
    type: 'credit_report', linked: 'Applicant · Thembi', added: '12 Apr 2026',
    retention: 'bureau_18m', reads: 1, purge: '12 Oct 2027', purgeWarn: true },
  { doc: 'Outgoing inspection · 3 Dorp', sub: '🔒 Tribunal hold',
    type: 'inspection', linked: 'Pienaar refund', added: '8 Apr 2026',
    retention: 'legal_hold', reads: 5, purge: 'Held · Tribunal', purgeHold: true },
  { doc: 'Mandate · J. van der Merwe', sub: 'Signed 4 Jan 2019 · renewed annually',
    type: 'mandate', linked: 'van der Merwe', added: '4 Jan 2019',
    retention: 'mandate_5y', reads: 12, purge: 'Rolling + 5y' },
]
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Vault33</span></div>
      <div class="page-header-row">
        <div>
          <h1>Vault33</h1>
          <p class="sub">Encrypted document store · Fernet per agency · every read audit-logged · retention automated.</p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="DSAR bundle"><Download :size="14" />DSAR bundle</button>
          <button class="btn" aria-label="Upload document"><Upload :size="14" />Upload</button>
          <button class="btn primary" aria-label="Retention report"><ShieldCheck :size="14" />Retention report</button>
        </div>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="label">Total documents</div><div class="value">2 148</div><div class="delta">+34 this week</div></div>
      <div class="stat"><div class="label">Purging this week</div><div class="value">12</div><div class="delta">bureau_18m · applicant_denied_18m</div></div>
      <div class="stat"><div class="label">Legal holds</div><div class="value">1</div><div class="delta">Tribunal · 3 Dorp refund</div></div>
      <div class="stat"><div class="label">DSAR requests YTD</div><div class="value">3</div><div class="delta">all fulfilled within 24h</div></div>
    </div>

    <div class="table-wrap">
      <table class="data">
        <thead>
          <tr><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Linked to</th><th scope="col">Added</th><th scope="col">Retention</th><th scope="col">Reads</th><th scope="col">Purge due</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.doc">
            <td><strong>{{ r.doc }}</strong><div class="muted">{{ r.sub }}</div></td>
            <td>{{ r.type }}</td>
            <td>{{ r.linked }}</td>
            <td>{{ r.added }}</td>
            <td>{{ r.retention }}</td>
            <td>{{ r.reads }}</td>
            <td :class="(!r.purgeWarn && !r.purgeHold) ? 'muted' : ''">
              <strong v-if="r.purgeWarn" style="color:var(--warn)">{{ r.purge }}</strong>
              <span v-else-if="r.purgeHold" class="badge refund">{{ r.purge }}</span>
              <template v-else>{{ r.purge }}</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

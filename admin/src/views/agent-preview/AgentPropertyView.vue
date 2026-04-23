<!--
  AgentPropertyView — Property god view (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-property.
  9 tabs: Overview / Lease / Tenants / Inspections / Maintenance / Ledger / Documents / Messages / Audit.

  Tab state is synced to ?tab= query param (WCAG / deep-link friendly).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  MessageCircle,
  FileText,
  Zap,
  Info,
  Users,
  Clock,
  FolderLock,
  CheckCircle2,
  Plus,
  Download,
  Upload,
  ShieldCheck,
  ClipboardList,
  ArrowRight,
  Receipt,
  Search,
  Eye,
  List,
  NotebookPen,
  ListChecks,
  FileSearch,
  Pencil,
  RotateCcw,
  Share2,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

type Tab =
  | 'overview' | 'lease' | 'tenants' | 'inspections'
  | 'maintenance' | 'ledger' | 'pg-docs' | 'pg-msg' | 'audit'

const VALID_TABS: Tab[] = [
  'overview', 'lease', 'tenants', 'inspections',
  'maintenance', 'ledger', 'pg-docs', 'pg-msg', 'audit',
]

function normaliseTab(raw: string | undefined): Tab {
  if (raw && (VALID_TABS as string[]).includes(raw)) return raw as Tab
  return 'overview'
}

const tab = computed<Tab>(() => normaliseTab(route.query.tab as string | undefined))

function setTab(name: Tab) {
  router.replace({ query: { ...route.query, tab: name } })
}
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb">
        <a @click.prevent="router.push('/agent/properties')" href="#">Properties</a>
        · <span>15 Andringa, Stellenbosch</span>
      </div>
      <div class="page-header-row">
        <div>
          <h1>15 Andringa, Stellenbosch</h1>
          <p class="sub">
            <span class="badge active"><span class="bullet" style="background:var(--ok)" />Active</span>
            &nbsp;·&nbsp; Erf 1420 · 3 bed · 2 bath · 180m² · R 15 200/mo
          </p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Message tenant"><MessageCircle :size="14" />Message tenant</button>
          <button class="btn" aria-label="Generate statement"><FileText :size="14" />Generate statement</button>
          <button class="btn primary" aria-label="Actions"><Zap :size="14" />Action</button>
        </div>
      </div>
    </div>

    <div class="timeline">
      <div class="timeline-label">12-month tenancy window · Mar 2026 → Feb 2027</div>
      <div class="timeline-bar">
        <div class="tl-month past">Mar</div>
        <div class="tl-month today">Apr</div>
        <div class="tl-month">May</div>
        <div class="tl-month">Jun<span class="marker" title="Rent escalation" /></div>
        <div class="tl-month">Jul</div>
        <div class="tl-month">Aug</div>
        <div class="tl-month">Sep</div>
        <div class="tl-month">Oct</div>
        <div class="tl-month">Nov</div>
        <div class="tl-month">Dec<span class="marker" title="Renewal window T-90" /></div>
        <div class="tl-month">Jan</div>
        <div class="tl-month">Feb<span class="marker" title="Lease end" /></div>
      </div>
      <div class="tl-legend"><span><i style="background:var(--accent)" />Events: escalation · renewal window · lease end</span></div>
    </div>

    <div class="tabs">
      <div :class="tab === 'overview' ? 'tab active' : 'tab'" @click="setTab('overview')">Overview</div>
      <div :class="tab === 'lease' ? 'tab active' : 'tab'" @click="setTab('lease')">Lease</div>
      <div :class="tab === 'tenants' ? 'tab active' : 'tab'" @click="setTab('tenants')">Tenants</div>
      <div :class="tab === 'inspections' ? 'tab active' : 'tab'" @click="setTab('inspections')">Inspections</div>
      <div :class="tab === 'maintenance' ? 'tab active' : 'tab'" @click="setTab('maintenance')">Maintenance <span class="count" style="margin-left:4px">2</span></div>
      <div :class="tab === 'ledger' ? 'tab active' : 'tab'" @click="setTab('ledger')">Ledger</div>
      <div :class="tab === 'pg-docs' ? 'tab active' : 'tab'" @click="setTab('pg-docs')">Documents</div>
      <div :class="tab === 'pg-msg' ? 'tab active' : 'tab'" @click="setTab('pg-msg')">Messages</div>
      <div :class="tab === 'audit' ? 'tab active' : 'tab'" @click="setTab('audit')">Audit</div>
    </div>

    <!-- Overview -->
    <div v-if="tab === 'overview'" class="pg-pane active">
      <div class="pgrid">
        <div>
          <div class="action-card">
            <h3>Next action</h3>
            <p>Monthly statement due to owner on 30 Apr (in 3 days). All rent received · no deductions pending.</p>
            <button class="btn"><FileText :size="14" />Generate statement now</button>
          </div>

          <div class="pcard">
            <h3><Info :size="14" />Property</h3>
            <dl class="kv">
              <dt>Address</dt><dd>15 Andringa St, Stellenbosch 7600</dd>
              <dt>Erf / portion</dt><dd>1420 / 0</dd>
              <dt>Type</dt><dd>House · 3 bed · 2 bath</dd>
              <dt>Size</dt><dd>180 m² erf / 142 m² under roof</dd>
              <dt>Owner</dt><dd>J. van der Merwe <span class="muted">(since 2019)</span></dd>
              <dt>Mandate</dt><dd>Exclusive · 12 months · auto-renewing</dd>
              <dt>Rates acc.</dt><dd>SB-108441</dd>
            </dl>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><Users :size="14" />Current tenancy</h3>
            <dl class="kv">
              <dt>Tenant</dt><dd>Vink family (Piet &amp; Anna + 2)</dd>
              <dt>Lease</dt><dd>1 Mar 2026 → 28 Feb 2027</dd>
              <dt>Rent</dt><dd>R 15 200/mo · escalates 6% 1 Mar</dd>
              <dt>Deposit</dt><dd>R 30 400 (held · interest accruing)</dd>
              <dt>Payment day</dt><dd>1st of month · EFT</dd>
              <dt>Consents</dt><dd>Credit ✓ · Marketing ✗ · Maintenance photos ✓</dd>
            </dl>
          </div>
        </div>

        <div>
          <div class="pcard">
            <h3><Clock :size="14" />Recent activity</h3>
            <div style="font-size:13px;color:var(--ink)">
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Rent received</strong> R 15 200<div class="muted" style="font-size:12px">1 Apr · bank reconciliation</div></div>
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Maintenance closed</strong> Geyser element<div class="muted" style="font-size:12px">28 Mar · R 2 400</div></div>
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Statement sent</strong> to owner<div class="muted" style="font-size:12px">31 Mar</div></div>
              <div style="padding:8px 0"><strong>Message</strong> from tenant<div class="muted" style="font-size:12px">26 Mar · thanks for quick geyser fix</div></div>
            </div>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><FolderLock :size="14" />Vault33</h3>
            <div style="font-size:13px">
              <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line)"><span>Lease 2026-27.pdf</span><CheckCircle2 :size="14" style="color:var(--ok)" /></div>
              <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line)"><span>Ingoing inspection.pdf</span><CheckCircle2 :size="14" style="color:var(--ok)" /></div>
              <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line)"><span>FICA — tenant ID</span><CheckCircle2 :size="14" style="color:var(--ok)" /></div>
              <div style="display:flex;justify-content:space-between;padding:6px 0"><span>Payslips (3 months)</span><CheckCircle2 :size="14" style="color:var(--ok)" /></div>
            </div>
            <button class="btn" style="width:100%;margin-top:10px"><Plus :size="14" />Upload document</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Lease -->
    <div v-if="tab === 'lease'" class="pg-pane active">
      <div class="pgrid">
        <div>
          <div class="pcard">
            <h3><FileText :size="14" />Lease — 2026/27 · v2</h3>
            <dl class="kv">
              <dt>Term</dt><dd>12 months · 1 Mar 2026 → 28 Feb 2027</dd>
              <dt>Rent</dt><dd>R 15 200/month · payable 1st · EFT</dd>
              <dt>Escalation</dt><dd>6% annually on renewal date</dd>
              <dt>Deposit</dt><dd>R 30 400 (2× rent)</dd>
              <dt>Utilities</dt><dd>Prepaid electricity · water on municipal account</dd>
              <dt>Template</dt><dd>WC Residential Fixed-Term v4.2</dd>
              <dt>Parties signed</dt><dd>Tenant ✓ 12 Jan · Owner ✓ 14 Jan · Agent ✓ 14 Jan</dd>
              <dt>PDF integrity</dt><dd><code style="font-family:'JetBrains Mono',monospace;font-size:11px">sha256: a7f2d3…</code></dd>
            </dl>
            <div style="margin-top:14px;display:flex;gap:8px">
              <button class="btn"><Download :size="14" />Download PDF</button>
              <button class="btn"><Plus :size="14" />Add addendum</button>
              <button class="btn"><RotateCcw :size="14" />Draft renewal</button>
            </div>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><ListChecks :size="14" />Clauses · 28 active</h3>
            <table class="data" style="border:none">
              <thead><tr><th scope="col">#</th><th scope="col">Clause</th><th scope="col">Status</th></tr></thead>
              <tbody>
                <tr><td>1</td><td>Parties &amp; definitions</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Standard</span></td></tr>
                <tr><td>4</td><td>Rent &amp; escalation</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Standard</span></td></tr>
                <tr><td>7</td><td>Deposit &amp; interest (RHA s5)</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Standard</span></td></tr>
                <tr><td>12</td><td>Pet clause · dog approved</td><td><span class="badge signing"><span class="bullet" style="background:var(--warn)" />Custom</span></td></tr>
                <tr><td>19</td><td>Early termination · 2-month notice</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Standard</span></td></tr>
                <tr><td>24</td><td>CPA cooling-off waiver</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Standard</span></td></tr>
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <div class="pcard">
            <h3><ShieldCheck :size="14" />Signing audit</h3>
            <div style="font-size:13px">
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Owner counter-signed</strong><div class="muted" style="font-size:12px">14 Jan · OTP · IP 41.0.245.x · Chrome</div></div>
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Agent signed</strong><div class="muted" style="font-size:12px">14 Jan · mobile · Sarah N.</div></div>
              <div style="padding:8px 0;border-bottom:1px solid var(--line)"><strong>Tenant signed</strong><div class="muted" style="font-size:12px">12 Jan · drawn · OTP 4421</div></div>
              <div style="padding:8px 0"><strong>Envelope sent</strong><div class="muted" style="font-size:12px">10 Jan · Sarah N.</div></div>
            </div>
            <button class="btn" style="width:100%;margin-top:10px"><ShieldCheck :size="14" />Integrity report</button>
          </div>
          <div class="pcard" style="margin-top:14px">
            <h3><Plus :size="14" />Addenda</h3>
            <div style="font-size:13px;color:var(--muted)">No addenda yet.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tenants -->
    <div v-if="tab === 'tenants'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Users :size="14" />Current tenants (2 adults + 2 children)</h3>
          <table class="data" style="border:none;margin-top:10px">
            <thead><tr><th scope="col">Name</th><th scope="col">Role</th><th scope="col">Phone</th><th scope="col">FICA</th><th scope="col">Credit</th><th scope="col">Consents</th></tr></thead>
            <tbody>
              <tr><td><strong>Piet Vink</strong><div class="muted">ID 8603105122088</div></td><td>Primary</td><td>082 451 9928</td><td><CheckCircle2 :size="14" style="color:var(--ok)" /> 12/1/26</td><td>TU 742 <span class="muted">(12/1/26)</span></td><td>Credit ✓ · Market ✗ · Media ✓</td></tr>
              <tr><td><strong>Anna Vink</strong><div class="muted">ID 8811030098082</div></td><td>Co-tenant</td><td>083 118 4429</td><td><CheckCircle2 :size="14" style="color:var(--ok)" /> 12/1/26</td><td>TU 698</td><td>Credit ✓ · Market ✓ · Media ✓</td></tr>
              <tr><td>Kai Vink <span class="muted">(14)</span></td><td>Minor</td><td>—</td><td class="muted">n/a</td><td class="muted">n/a</td><td>Parental consent on file</td></tr>
              <tr><td>Lea Vink <span class="muted">(11)</span></td><td>Minor</td><td>—</td><td class="muted">n/a</td><td class="muted">n/a</td><td>Parental consent on file</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pcard" style="margin-top:14px">
          <h3><Clock :size="14" />Previous tenants</h3>
          <table class="data" style="border:none;margin-top:10px">
            <thead><tr><th scope="col">Name</th><th scope="col">Period</th><th scope="col">Rent</th><th scope="col">Outcome</th></tr></thead>
            <tbody>
              <tr><td>H. Stofberg</td><td>1 Mar 2023 → 28 Feb 2026</td><td class="money">R 13 200–14 400</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Clean exit · full refund</span></td></tr>
              <tr><td>M. Scholtz (lodger)</td><td>1 Jun 2022 → 30 Nov 2022</td><td class="money">R 4 500 (room)</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Short-term · no dispute</span></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Inspections -->
    <div v-if="tab === 'inspections'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><ClipboardList :size="14" />Inspection history</h3>
          <table class="data" style="border:none;margin-top:10px">
            <thead><tr><th scope="col">Date</th><th scope="col">Type</th><th scope="col">Outcome</th><th scope="col">Deductions</th><th scope="col">Agent</th><th scope="col">PDF</th></tr></thead>
            <tbody>
              <tr><td><strong>15 Jan 2026 · 09:00</strong></td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Ingoing</span></td><td>Clean · 1 note (stove knob loose)</td><td class="muted">—</td><td>Sarah N.</td><td><a href="#" style="color:var(--navy)">ingoing.pdf</a></td></tr>
              <tr><td>1 Sep 2025</td><td><span class="badge marketing"><span class="bullet" style="background:var(--info)" />Mid</span></td><td>Noted damp patch bathroom · scheduled repair</td><td class="muted">—</td><td>Dan T.</td><td><a href="#" style="color:var(--navy)">mid.pdf</a></td></tr>
              <tr><td>28 Feb 2023</td><td><span class="badge" style="background:var(--accent-soft);color:var(--accent)">Outgoing</span></td><td>Clean (previous tenant Stofberg)</td><td class="muted">—</td><td>Sarah N.</td><td><a href="#" style="color:var(--navy)">outgoing.pdf</a></td></tr>
              <tr><td>1 Mar 2023</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Ingoing</span></td><td>Clean</td><td class="muted">—</td><td>Sarah N.</td><td><a href="#" style="color:var(--navy)">ingoing.pdf</a></td></tr>
            </tbody>
          </table>
          <button class="btn" style="margin-top:14px"><Plus :size="14" />Schedule mid-tenancy inspection</button>
        </div>
        <div class="pcard" style="margin-top:14px">
          <h3>Ingoing photo set (excerpt)</h3>
          <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:10px">
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Kitchen</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Living</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Bedroom 1</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Bedroom 2</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Bathroom</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#E4E4EE,#EFEFF5);border-radius:8px;display:flex;align-items:flex-end;padding:6px;font-size:11px;color:var(--muted)">Meter</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Maintenance -->
    <div v-if="tab === 'maintenance'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="stats" style="padding:0;margin-bottom:14px">
          <div class="stat"><div class="label">Open</div><div class="value">2</div><div class="delta">1 dispatched · 1 quoted</div></div>
          <div class="stat"><div class="label">Closed YTD</div><div class="value">7</div><div class="delta">avg 4.2d to close</div></div>
          <div class="stat"><div class="label">Spend YTD</div><div class="value">R 12 840</div><div class="delta">6% of rent collected</div></div>
          <div class="stat"><div class="label">Tenant rating</div><div class="value">4.8★</div><div class="delta">across 7 jobs</div></div>
        </div>
        <div class="pcard">
          <h3><Wrench :size="14" />Tickets</h3>
          <table class="data" style="border:none;margin-top:10px">
            <thead><tr><th scope="col">#</th><th scope="col">Issue</th><th scope="col">Category</th><th scope="col">Supplier</th><th scope="col">State</th><th scope="col">Cost</th><th scope="col">Closed</th></tr></thead>
            <tbody>
              <tr><td>#228</td><td>Door lock failure</td><td>Locks/security</td><td>EZ Locksmith</td><td><span class="badge signing"><span class="bullet" style="background:var(--warn)" />Dispatched · ETA 11:00</span></td><td class="money">R 1 850</td><td class="muted">—</td></tr>
              <tr><td>#224</td><td>Kitchen tap drip</td><td>Plumbing</td><td>SAPlumb</td><td><span class="badge marketing"><span class="bullet" style="background:var(--info)" />Quoted · under threshold</span></td><td class="money">R 780</td><td class="muted">—</td></tr>
              <tr><td>#219</td><td>Geyser element</td><td>Plumbing</td><td>SAPlumb</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Closed</span></td><td class="money">R 2 400</td><td>28 Mar 2026</td></tr>
              <tr><td>#207</td><td>Paint touch-ups</td><td>Handyman</td><td>Quick Fix Co.</td><td><span class="badge active"><span class="bullet" style="background:var(--ok)" />Closed</span></td><td class="money">R 1 200</td><td>14 Feb 2026</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Ledger -->
    <div v-if="tab === 'ledger'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="stats" style="padding:0;margin-bottom:14px">
          <div class="stat"><div class="label">Rent collected YTD</div><div class="value">R 121 600</div><div class="delta">8 months paid on time</div></div>
          <div class="stat"><div class="label">Commission earned</div><div class="value">R 9 728</div><div class="delta">8% of collected</div></div>
          <div class="stat"><div class="label">Maintenance deducted</div><div class="value">R 3 600</div><div class="delta">from owner account</div></div>
          <div class="stat"><div class="label">Net to owner YTD</div><div class="value">R 108 272</div><div class="delta">via EFT monthly</div></div>
        </div>
        <div class="pcard">
          <h3><Receipt :size="14" />Journal entries (last 10)</h3>
          <table class="ledger" style="margin-top:10px">
            <thead><tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Debit</th><th scope="col">Credit</th><th scope="col" class="amt">Amount</th></tr></thead>
            <tbody>
              <tr><td>1 Apr 2026</td><td>Rent received · Vink</td><td>Trust: Owner</td><td>Rent income</td><td class="amt money">R 15 200.00</td></tr>
              <tr><td>1 Apr 2026</td><td>Commission · 8%</td><td>Trust: Owner</td><td>Business: Commission</td><td class="amt money">−R 1 216.00</td></tr>
              <tr><td>1 Apr 2026</td><td>Maintenance #219 · geyser</td><td>Trust: Owner</td><td>Supplier: SAPlumb</td><td class="amt money">−R 2 400.00</td></tr>
              <tr><td>1 Apr 2026</td><td>EFT to owner</td><td>Trust: Owner</td><td>Bank: Disbursement</td><td class="amt money">−R 11 584.00</td></tr>
              <tr><td>28 Mar 2026</td><td>Invoice · SAPlumb #219</td><td>Expense</td><td>Supplier: SAPlumb</td><td class="amt money">R 2 400.00</td></tr>
              <tr><td>1 Mar 2026</td><td>Rent received · Vink</td><td>Trust: Owner</td><td>Rent income</td><td class="amt money">R 15 200.00</td></tr>
              <tr><td>1 Mar 2026</td><td>Deposit interest accrual</td><td>Trust: Interest</td><td>Tenant: Vink</td><td class="amt money">R 142.00</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Documents -->
    <div v-if="tab === 'pg-docs'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><FolderLock :size="14" />Vault33 · documents for this property (23)</h3>
          <table class="data" style="border:none;margin-top:10px">
            <thead><tr><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Added</th><th scope="col">Retention</th><th scope="col">Reads</th><th scope="col"></th></tr></thead>
            <tbody>
              <tr><td><strong>Lease 2026-27.pdf</strong><div class="muted">sha: a7f2… · 3.2 MB</div></td><td>signed_lease</td><td>14 Jan 2026</td><td>rha_lease_5y → 2032</td><td>7</td><td><a href="#" style="color:var(--navy)" aria-label="View Lease 2026-27.pdf"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Ingoing inspection.pdf</strong><div class="muted">42 photos · dual-signed</div></td><td>inspection</td><td>15 Jan 2026</td><td>inspection_3y</td><td>2</td><td><a href="#" style="color:var(--navy)" aria-label="View Ingoing inspection.pdf"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>ID copy · P. Vink</strong></td><td>identity</td><td>13 Jan 2026</td><td>fica_5y</td><td>3</td><td><a href="#" style="color:var(--navy)" aria-label="View ID copy P. Vink"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>ID copy · A. Vink</strong></td><td>identity</td><td>13 Jan 2026</td><td>fica_5y</td><td>2</td><td><a href="#" style="color:var(--navy)" aria-label="View ID copy A. Vink"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Payslips · P. Vink (3mo)</strong></td><td>proof_income</td><td>13 Jan 2026</td><td>fica_5y</td><td>4</td><td><a href="#" style="color:var(--navy)" aria-label="View Payslips P. Vink"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Credit report · P. Vink</strong><div class="muted">TransUnion · 742</div></td><td>credit_report</td><td>12 Jan 2026</td><td><strong style="color:var(--warn)">bureau_18m → Jul 2027</strong></td><td>1</td><td><a href="#" style="color:var(--navy)" aria-label="View Credit report P. Vink"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Invoice · SAPlumb #219</strong></td><td>supplier_invoice</td><td>28 Mar 2026</td><td>tax_5y</td><td>2</td><td><a href="#" style="color:var(--navy)" aria-label="View Invoice SAPlumb #219"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Statement · March 2026</strong></td><td>owner_statement</td><td>31 Mar 2026</td><td>tax_5y</td><td>1 <span class="muted">(owner)</span></td><td><a href="#" style="color:var(--navy)" aria-label="View Statement March 2026"><Eye :size="14" /></a></td></tr>
              <tr><td><strong>Consent artefacts (4)</strong></td><td>consent</td><td>12–15 Jan 2026</td><td>relationship+3y</td><td>—</td><td><a href="#" style="color:var(--navy)" aria-label="View Consent artefacts"><List :size="14" /></a></td></tr>
            </tbody>
          </table>
          <div style="display:flex;gap:8px;margin-top:14px">
            <button class="btn"><Upload :size="14" />Upload</button>
            <button class="btn"><Download :size="14" />DSAR bundle</button>
            <button class="btn"><Share2 :size="14" />Gateway share</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="tab === 'pg-msg'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><MessageCircle :size="14" />All threads involving this property (3)</h3>
          <div style="margin-top:14px">
            <div style="padding:14px;border:1px solid var(--line);border-radius:10px;margin-bottom:10px;display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center">
              <div class="avatar" style="width:36px;height:36px;font-size:12px">PV</div>
              <div><strong>Piet Vink (tenant) · 14 msgs · 3 channels</strong><div class="muted" style="font-size:12px">Latest: "Will do, 5 stars already 👍" · WhatsApp · 2m ago</div></div>
              <button class="btn ghost" aria-label="Open Piet Vink thread"><ArrowRight :size="14" /></button>
            </div>
            <div style="padding:14px;border:1px solid var(--line);border-radius:10px;margin-bottom:10px;display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center">
              <div class="avatar" style="width:36px;height:36px;font-size:12px;background:linear-gradient(135deg,#3B5BD9,var(--ok))">JvdM</div>
              <div><strong>J. van der Merwe (owner) · 8 msgs · email</strong><div class="muted" style="font-size:12px">Latest: "Approved the quote…" · Email · 1h ago</div></div>
              <button class="btn ghost" aria-label="Open J. van der Merwe thread"><ArrowRight :size="14" /></button>
            </div>
            <div style="padding:14px;border:1px solid var(--line);border-radius:10px;display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center">
              <div class="avatar" style="width:36px;height:36px;font-size:12px;background:linear-gradient(135deg,#8B5CF6,#F59E0B)">EZ</div>
              <div><strong>EZ Locksmith · ticket #228 · 5 msgs · SMS</strong><div class="muted" style="font-size:12px">Latest: "ETA 11:00 today. Bringing spare cylinder." · 2h ago</div></div>
              <button class="btn ghost" aria-label="Open EZ Locksmith thread"><ArrowRight :size="14" /></button>
            </div>
          </div>
        </div>
        <div class="pcard" style="margin-top:14px">
          <h3><NotebookPen :size="14" />Internal notes (team-only · 2)</h3>
          <div style="background:var(--warn-soft);border-left:3px solid var(--warn);padding:10px 14px;border-radius:6px;font-size:13px;margin-top:10px"><strong>Sarah N · 14 Apr 09:20</strong><br>Tenant very happy with geyser response — worth flagging for renewal discussion.</div>
          <div style="background:var(--warn-soft);border-left:3px solid var(--warn);padding:10px 14px;border-radius:6px;font-size:13px;margin-top:8px"><strong>Dan T · 2 Apr 15:12</strong><br>Owner prefers email over calls — update mandate.</div>
        </div>
      </div>
    </div>

    <!-- Audit -->
    <div v-if="tab === 'audit'" class="pg-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Search :size="14" />Full audit trail (last 30 events)</h3>
          <div style="margin-top:14px;font-family:'JetBrains Mono',monospace;font-size:12px">
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">17 Apr · 09:14:22</span><span style="color:var(--info);font-weight:600">READ</span><span>Sarah N. opened Lease 2026-27.pdf · purpose="renewal prep" · via=admin_ui</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Apr · 09:20:11</span><span style="color:var(--navy);font-weight:600">WRITE</span><span>Sarah N. added internal note on thread thr_8a21</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Apr · 09:16:08</span><span style="color:var(--ok);font-weight:600">MSG</span><span>WhatsApp inbound · tenant Piet Vink · msg_7g1h</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Apr · 09:15:02</span><span style="color:var(--ok);font-weight:600">MSG</span><span>In-app outbound · Sarah N → Piet Vink</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Apr · 09:12:55</span><span style="color:var(--ok);font-weight:600">MSG</span><span>WhatsApp inbound · tenant · "geyser fixed"</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">1 Apr · 08:04:21</span><span style="color:var(--accent);font-weight:600">LEDGER</span><span>System: bank match · R 15 200 · ref VINK-APR</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">1 Apr · 08:04:22</span><span style="color:var(--accent);font-weight:600">LEDGER</span><span>System: journal #j_1184 · rent-received</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">28 Mar · 16:42:08</span><span style="color:var(--warn);font-weight:600">GATE</span><span>Gate 3 · auto-approved · under threshold · ticket #219</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">28 Mar · 14:10:44</span><span style="color:var(--navy);font-weight:600">WRITE</span><span>Supplier SAPlumb uploaded invoice · #219 · R 2 400</span></div>
            <div style="padding:10px 0;border-bottom:1px solid var(--line);display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Jan · 11:22:17</span><span style="color:var(--navy);font-weight:600">WRITE</span><span>Owner countersigned lease · OTP · ip_hash=3c8a…</span></div>
            <div style="padding:10px 0;display:grid;grid-template-columns:180px 120px 1fr;gap:12px;color:var(--ink)"><span style="color:var(--muted)">14 Jan · 11:21:02</span><span style="color:var(--info);font-weight:600">STATE</span><span>Transition SIGNING → ACTIVE · actor=system</span></div>
          </div>
          <button class="btn" style="margin-top:14px"><Download :size="14" />Export full log (CSV)</button>
        </div>
      </div>
    </div>
  </section>
</template>

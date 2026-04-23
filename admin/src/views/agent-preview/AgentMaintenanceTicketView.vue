<!--
  AgentMaintenanceTicketView — Ticket #230 god view (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-maintenance-ticket.
  7 tabs: Overview / Quote / Dispatch / Photos / Invoice / Timeline / Messages.

  Tab state is synced to ?tab= query param (WCAG / deep-link friendly).
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Wrench,
  AlertTriangle,
  MessageCircle,
  Phone,
  Zap,
  Info,
  CheckCircle2,
  ShieldCheck,
  Circle,
  Image,
  User,
  Building2,
  FileText,
  RefreshCw,
  PlusCircle,
  XCircle,
  Mail,
  Bell,
  Mic,
  NotebookPen,
  RotateCcw,
  Receipt,
  Send,
  Clock,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

type Tab = 'overview' | 'quote' | 'dispatch' | 'photos' | 'invoice' | 'timeline' | 'messages'

const VALID_TABS: Tab[] = ['overview', 'quote', 'dispatch', 'photos', 'invoice', 'timeline', 'messages']

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
        <a @click.prevent="router.push('/agent/maintenance')" href="#">Maintenance</a>
        · <span>#230 · 22 Plein geyser</span>
      </div>
      <div class="page-header-row">
        <div>
          <h1>#230 · Geyser replacement — 22 Plein</h1>
          <p class="sub">
            <span class="badge" style="background:#F3E8FF;color:#7C3AED">
              <span class="bullet" style="background:#7C3AED" />Gate 3 · owner decision pending
            </span>
            &nbsp;·&nbsp; <Wrench :size="13" style="display:inline;vertical-align:middle" /> Plumbing
            &nbsp;·&nbsp; <AlertTriangle :size="13" style="display:inline;vertical-align:middle;color:var(--warn)" /> High urgency
            &nbsp;·&nbsp; Logged 1d 1h ago by tenant K. Jacobs
          </p>
        </div>
        <div class="page-actions">
          <button class="btn" aria-label="Message tenant"><MessageCircle :size="14" />Message tenant</button>
          <button class="btn" aria-label="Call owner"><Phone :size="14" />Call owner</button>
          <button class="btn primary" aria-label="Actions"><Zap :size="14" />Actions</button>
        </div>
      </div>
    </div>

    <!-- Gate 3 prominence strip -->
    <div class="alert-strip danger">
      <ShieldCheck :size="14" />
      <strong>Gate 3 — owner approval required</strong> · quote R 8 200 exceeds R 3 000 threshold · owner J. van der Merwe silent 25h (SLA breach in 23h)
      <button class="btn" style="margin-left:auto;border-color:var(--danger);color:var(--danger)" aria-label="Chase owner by email"><Mail :size="14" />Chase owner</button>
      <button class="btn primary" style="background:var(--danger);border-color:var(--danger)" aria-label="Override emergency"><ShieldCheck :size="14" />Override (emergency)</button>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <div :class="tab === 'overview' ? 'tab active' : 'tab'" @click="setTab('overview')">Overview</div>
      <div :class="tab === 'quote' ? 'tab active' : 'tab'" @click="setTab('quote')">Quote <span class="count" style="margin-left:4px">1</span></div>
      <div :class="tab === 'dispatch' ? 'tab active' : 'tab'" @click="setTab('dispatch')">Dispatch</div>
      <div :class="tab === 'photos' ? 'tab active' : 'tab'" @click="setTab('photos')">Photos <span class="count" style="margin-left:4px">6</span></div>
      <div :class="tab === 'invoice' ? 'tab active' : 'tab'" @click="setTab('invoice')">Invoice</div>
      <div :class="tab === 'timeline' ? 'tab active' : 'tab'" @click="setTab('timeline')">Timeline</div>
      <div :class="tab === 'messages' ? 'tab active' : 'tab'" @click="setTab('messages')">Messages <span class="count" style="margin-left:4px">8</span></div>
    </div>

    <!-- Overview -->
    <div v-if="tab === 'overview'" class="mt-pane active">
      <div class="pgrid">
        <div>
          <div class="action-card">
            <h3>Next action</h3>
            <p>Owner silent for 25h — SLA breaches in 23h. Chase via phone + WhatsApp. If no response in 12h and tenant has no hot water overnight, emergency override possible per mandate clause 8.2.</p>
            <div style="display:flex;gap:8px">
              <button class="btn"><Phone :size="14" />Call owner</button>
              <button class="btn"><Mail :size="14" />WhatsApp chase</button>
            </div>
          </div>

          <div class="pcard">
            <h3><Info :size="14" />Problem</h3>
            <div style="font-size:13px;margin-bottom:12px">
              Geyser stopped heating. Tenant reports no hot water since yesterday morning. Element tested — short to earth. Geyser is 9 years old (original install per ingoing inspection) so replacement rather than repair is recommended. Quote includes Kwikot 150L vertical, isolator, drip tray, SANS compliance certificate.
            </div>
            <dl class="kv">
              <dt>Property</dt><dd><a href="#" style="color:var(--navy);font-weight:500">22 Plein, Stellenbosch · Unit 4A</a></dd>
              <dt>Tenant</dt><dd>K. Jacobs <span class="muted">(lease starts 1 May — currently in signing)</span></dd>
              <dt>Owner</dt><dd>J. van der Merwe</dd>
              <dt>Logged by</dt><dd>Tenant · in-app · 16 Apr 09:42</dd>
              <dt>Category</dt><dd>Plumbing · geyser</dd>
              <dt>Urgency</dt><dd>High (no hot water)</dd>
              <dt>Cost bearer</dt><dd>Owner <span class="muted">(fair wear and tear · 9-year-old unit)</span></dd>
              <dt>Insurance?</dt><dd>Check — owner's home contents may cover water damage, not replacement</dd>
            </dl>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><CheckCircle2 :size="14" />Lifecycle</h3>
            <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:10px">
              <div style="padding:10px;background:var(--ok-soft);border-radius:8px;text-align:center;font-size:12px">
                <CheckCircle2 :size="18" style="color:var(--ok)" />
                <div style="font-weight:600;margin-top:4px">Logged</div>
                <div class="muted" style="font-size:11px">16 Apr 09:42</div>
              </div>
              <div style="padding:10px;background:var(--ok-soft);border-radius:8px;text-align:center;font-size:12px">
                <CheckCircle2 :size="18" style="color:var(--ok)" />
                <div style="font-weight:600;margin-top:4px">Triaged</div>
                <div class="muted" style="font-size:11px">16 Apr 10:15 · Sarah</div>
              </div>
              <div style="padding:10px;background:var(--ok-soft);border-radius:8px;text-align:center;font-size:12px">
                <CheckCircle2 :size="18" style="color:var(--ok)" />
                <div style="font-weight:600;margin-top:4px">Quoted</div>
                <div class="muted" style="font-size:11px">16 Apr 14:20 · SAPlumb</div>
              </div>
              <div style="padding:10px;background:#F3E8FF;border:2px solid #7C3AED;border-radius:8px;text-align:center;font-size:12px">
                <ShieldCheck :size="18" style="color:#7C3AED" />
                <div style="font-weight:600;margin-top:4px">Gate 3</div>
                <div style="color:#7C3AED;font-size:11px;font-weight:500">Pending · 25h</div>
              </div>
              <div style="padding:10px;background:var(--line);border-radius:8px;text-align:center;font-size:12px;opacity:.5">
                <Circle :size="18" />
                <div style="font-weight:600;margin-top:4px">Dispatch</div>
                <div class="muted" style="font-size:11px">—</div>
              </div>
            </div>
          </div>
        </div>

        <div>
          <div class="pcard">
            <h3><Image :size="14" />Tenant photos (3)</h3>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px">
              <div style="aspect-ratio:1;background:linear-gradient(135deg,#334,#556);border-radius:8px;display:flex;align-items:flex-end;padding:6px;color:#fff;font-size:11px;position:relative">
                <span>Geyser cupboard</span>
              </div>
              <div style="aspect-ratio:1;background:linear-gradient(135deg,#433,#655);border-radius:8px;display:flex;align-items:flex-end;padding:6px;color:#fff;font-size:11px">Element</div>
              <div style="aspect-ratio:1;background:linear-gradient(135deg,#343,#565);border-radius:8px;display:flex;align-items:flex-end;padding:6px;color:#fff;font-size:11px;grid-column:1/-1">Drip tray (wet)</div>
            </div>
            <div style="margin-top:10px;font-size:12px;color:var(--muted)">
              <Mic :size="12" style="display:inline;vertical-align:middle;color:var(--accent)" /> Voice note · 14s · "No hot water since yesterday…"
              <a href="#" style="color:var(--navy);margin-left:8px">▶ Play</a>
            </div>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><User :size="14" />Tenant</h3>
            <dl class="kv">
              <dt>Name</dt><dd>K. Jacobs</dd>
              <dt>Phone</dt><dd>084 007 1144</dd>
              <dt>Lease</dt><dd>Pending · starts 1 May</dd>
              <dt>Note</dt><dd class="muted" style="font-size:12px">Not yet tenant of record — issue reported during walk-through. Landlord is liable regardless.</dd>
            </dl>
            <button class="btn" style="width:100%;margin-top:10px"><MessageCircle :size="14" />Open thread</button>
          </div>

          <div class="pcard" style="margin-top:14px">
            <h3><Building2 :size="14" />Property history</h3>
            <div style="font-size:12px">
              <div style="padding:6px 0;border-bottom:1px solid var(--line)"><strong>#158</strong> · Mar 2024 · Paint · R 2 800 · Quick Fix</div>
              <div style="padding:6px 0;border-bottom:1px solid var(--line)"><strong>#097</strong> · Aug 2023 · Geyser valve · R 1 200 · SAPlumb</div>
              <div style="padding:6px 0"><strong>#042</strong> · Feb 2023 · Paint · R 3 400 · Quick Fix</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quote -->
    <div v-if="tab === 'quote'" class="mt-pane active">
      <div class="pgrid">
        <div>
          <div class="pcard">
            <h3><FileText :size="14" />Quote — SAPlumb · #Q-2026-0418</h3>
            <dl class="kv">
              <dt>Received</dt><dd>16 Apr 14:20 · via supplier portal</dd>
              <dt>Valid until</dt><dd>23 Apr 2026 <span class="muted">(7 days)</span></dd>
              <dt>Supplier</dt><dd>SAPlumb (Pty) Ltd · 4.6★ · 47 jobs with this agency</dd>
              <dt>VAT status</dt><dd>Registered · 4150228812</dd>
              <dt>PDF</dt><dd><a href="#" style="color:var(--navy)"><FileText :size="13" style="display:inline;vertical-align:middle" /> quote-2026-0418.pdf</a> · 247 KB</dd>
            </dl>

            <table class="data" style="border:none;margin-top:14px">
              <thead><tr><th scope="col">Item</th><th scope="col">Qty</th><th scope="col" class="amt">Unit</th><th scope="col" class="amt">Total</th></tr></thead>
              <tbody>
                <tr><td><strong>Kwikot 150L vertical geyser</strong><div class="muted" style="font-size:12px">5-yr warranty · SANS compliant</div></td><td>1</td><td class="amt money">R 4 200</td><td class="amt money">R 4 200</td></tr>
                <tr><td>Isolator switch + electrical</td><td>1</td><td class="amt money">R 420</td><td class="amt money">R 420</td></tr>
                <tr><td>Drip tray + overflow pipe</td><td>1</td><td class="amt money">R 380</td><td class="amt money">R 380</td></tr>
                <tr><td>Vacuum breaker + isolation valve</td><td>1</td><td class="amt money">R 290</td><td class="amt money">R 290</td></tr>
                <tr><td>Labour (4h · 2 technicians)</td><td>8</td><td class="amt money">R 220</td><td class="amt money">R 1 760</td></tr>
                <tr><td>SANS 10254 electrical CoC</td><td>1</td><td class="amt money">R 450</td><td class="amt money">R 450</td></tr>
                <tr><td>Disposal · old geyser</td><td>1</td><td class="amt money">R 150</td><td class="amt money">R 150</td></tr>
                <tr style="background:var(--paper)"><td colspan="3"><strong>Subtotal (excl VAT)</strong></td><td class="amt money"><strong>R 7 130.43</strong></td></tr>
                <tr style="background:var(--paper)"><td colspan="3">VAT @ 15%</td><td class="amt money">R 1 069.57</td></tr>
                <tr style="background:var(--navy-soft)"><td colspan="3"><strong>Total (incl VAT)</strong></td><td class="amt money"><strong style="font-size:15px;color:var(--navy)">R 8 200.00</strong></td></tr>
              </tbody>
            </table>

            <div style="display:flex;gap:8px;margin-top:14px">
              <button class="btn"><RotateCcw :size="14" />Request revision</button>
              <button class="btn"><PlusCircle :size="14" />Add 2nd quote</button>
              <button class="btn" style="margin-left:auto"><XCircle :size="14" />Reject quote</button>
              <button class="btn primary"><CheckCircle2 :size="14" />Accept &amp; dispatch</button>
            </div>
          </div>
        </div>

        <div>
          <div class="pcard" style="border-left:3px solid #7C3AED">
            <h3><ShieldCheck :size="14" style="color:#7C3AED;display:inline;vertical-align:middle" /> Gate 3 · owner approval</h3>
            <dl class="kv">
              <dt>Threshold</dt><dd>R 3 000 per mandate</dd>
              <dt>Quote</dt><dd class="money" style="color:var(--navy);font-weight:600">R 8 200.00</dd>
              <dt>Gate required</dt><dd>Yes (2.7× threshold)</dd>
              <dt>Sent</dt><dd>16 Apr 14:35 · email + WhatsApp</dd>
              <dt>Owner</dt><dd>J. van der Merwe</dd>
              <dt>Response</dt><dd><strong style="color:var(--warn)">Silent 25h</strong></dd>
              <dt>SLA</dt><dd><strong style="color:var(--danger)">Breach in 23h</strong></dd>
            </dl>

            <div style="margin-top:14px;padding:10px 12px;background:var(--paper);border-radius:8px;font-size:12px">
              <strong style="color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.04em">Owner chase log</strong>
              <div style="margin-top:6px"><Mail :size="12" style="display:inline;vertical-align:middle" /> 16 Apr 14:35 · Email sent · delivered ✓ · opened ✗</div>
              <div><MessageCircle :size="12" style="display:inline;vertical-align:middle" /> 16 Apr 14:35 · WhatsApp sent · delivered ✓ · read ✓ 15:02</div>
              <div><Bell :size="12" style="display:inline;vertical-align:middle" /> 17 Apr 09:00 · Reminder sent · no response</div>
            </div>

            <div style="display:flex;flex-direction:column;gap:6px;margin-top:14px">
              <button class="btn"><Phone :size="14" />Call owner now</button>
              <button class="btn"><Mail :size="14" />Send SLA warning</button>
              <button class="btn" style="border-color:var(--danger);color:var(--danger)"><ShieldCheck :size="14" />Emergency override</button>
            </div>

            <div style="margin-top:10px;font-size:11px;color:var(--muted);line-height:1.5">
              <strong>Override basis:</strong> mandate clause 8.2 — agent may authorise up to R 10 000 without owner consent for "any loss of habitability including no hot water &gt; 48h". Audit-logged. Owner notified post-facto.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Dispatch -->
    <div v-if="tab === 'dispatch'" class="mt-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Wrench :size="14" />Dispatch (pending Gate 3 approval)</h3>
          <p class="muted" style="font-size:13px;margin-top:8px">
            Once owner approves (or agent overrides), SAPlumb will be auto-dispatched and this pane populates with live tracking.
          </p>

          <div style="margin-top:20px;padding:16px;background:var(--paper);border-radius:10px">
            <div style="font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin-bottom:10px">Planned dispatch</div>
            <dl class="kv">
              <dt>Supplier</dt><dd>SAPlumb (Pty) Ltd · 4.6★</dd>
              <dt>Primary contact</dt><dd>J. Adams · 082 118 4420</dd>
              <dt>Proposed date</dt><dd>Fri 19 Apr · 08:00–12:00 slot</dd>
              <dt>Access</dt><dd>Coordinate with K. Jacobs (tenant) · 084 007 1144</dd>
              <dt>Access notes</dt><dd class="muted" style="font-size:12px">Geyser cupboard in passage · water main shutoff at gate · DB board in kitchen</dd>
              <dt>Special instructions</dt><dd class="muted" style="font-size:12px">Take photos of removed unit for owner (possible insurance claim)</dd>
              <dt>Estimated duration</dt><dd>4 hours</dd>
              <dt>Water off</dt><dd>2 hours (tenant informed)</dd>
              <dt>Power off</dt><dd>1 hour during isolator swap</dd>
            </dl>
          </div>

          <div style="margin-top:14px;font-size:12px;color:var(--muted)">
            <Info :size="12" style="display:inline;vertical-align:middle" /> Before/after photos are mandatory for this job value. Supplier prompted in their app.
          </div>
        </div>
      </div>
    </div>

    <!-- Photos -->
    <div v-if="tab === 'photos'" class="mt-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Image :size="14" />Photos · 6 total</h3>

          <div style="font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin:14px 0 8px">Tenant submitted (3) · 16 Apr 09:42</div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#334,#556);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Geyser cupboard</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#433,#655);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Element close-up</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#343,#565);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Drip tray wet</div>
          </div>

          <div style="font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin:20px 0 8px">Supplier quote (3) · SAPlumb · 16 Apr 14:20</div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#335,#557);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Current geyser</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#353,#575);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Install angle</div>
            <div style="aspect-ratio:1;background:linear-gradient(135deg,#533,#755);border-radius:8px;display:flex;align-items:flex-end;padding:8px;color:#fff;font-size:11px;cursor:pointer">Ingoing insp (2026)</div>
          </div>

          <div style="font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin:20px 0 8px">Before/after (on dispatch) · not yet available</div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
            <div style="aspect-ratio:1;background:var(--line);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted-2);font-size:11px;border:2px dashed var(--line-2)">Before</div>
            <div style="aspect-ratio:1;background:var(--line);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted-2);font-size:11px;border:2px dashed var(--line-2)">After</div>
            <div style="aspect-ratio:1;background:var(--line);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted-2);font-size:11px;border:2px dashed var(--line-2)">CoC</div>
            <div style="aspect-ratio:1;background:var(--line);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted-2);font-size:11px;border:2px dashed var(--line-2)">Disposal</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Invoice -->
    <div v-if="tab === 'invoice'" class="mt-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Receipt :size="14" />Invoice (awaits job completion)</h3>
          <div class="empty" style="padding:40px 0">
            <Receipt :size="48" />
            <h2>Not yet invoiced</h2>
            <p>Invoice auto-requested when supplier marks Done + tenant confirms. Match against quote; &gt;10% variance triggers re-approval.</p>
          </div>

          <div style="margin-top:10px;padding:16px;background:var(--paper);border-radius:10px">
            <div style="font-size:11px;text-transform:uppercase;color:var(--muted);letter-spacing:.06em;margin-bottom:10px">Payment rules (per mandate)</div>
            <dl class="kv">
              <dt>Payment from</dt><dd>Owner trust balance · ABSA-4412</dd>
              <dt>Terms</dt><dd>14 days from invoice</dd>
              <dt>Reconcile</dt><dd>Appears on April owner statement as separate line</dd>
              <dt>Variance rule</dt><dd>&gt;10% over quote → re-approval required</dd>
              <dt>Supplier payment history</dt><dd>47 jobs · all paid on time · no disputes</dd>
            </dl>
          </div>
        </div>
      </div>
    </div>

    <!-- Timeline -->
    <div v-if="tab === 'timeline'" class="mt-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><Clock :size="14" />Ticket timeline</h3>
          <div style="margin-top:14px;font-size:13px">
            <div style="padding:12px 14px;border-left:2px solid var(--warn);background:var(--warn-soft);border-radius:0 8px 8px 0;margin-bottom:10px">
              <strong>17 Apr 09:00</strong> · Reminder sent to owner
              <div class="muted" style="font-size:12px">No response · SLA warning escalated to Sarah N.</div>
            </div>
            <div style="padding:12px 14px;border-left:2px solid var(--info);background:var(--info-soft);border-radius:0 8px 8px 0;margin-bottom:10px">
              <strong>16 Apr 15:02</strong> · Owner read WhatsApp
              <div class="muted" style="font-size:12px">Delivered ✓ · Read ✓ · no reply</div>
            </div>
            <div style="padding:12px 14px;border-left:2px solid #7C3AED;background:#F3E8FF;border-radius:0 8px 8px 0;margin-bottom:10px">
              <strong>16 Apr 14:35</strong> · Gate 3 raised
              <div class="muted" style="font-size:12px">Quote R 8 200 &gt; R 3 000 threshold · owner notified by email + WhatsApp · SLA 48h</div>
            </div>
            <div style="padding:12px 14px;border-left:2px solid var(--ok);background:var(--ok-soft);border-radius:0 8px 8px 0;margin-bottom:10px">
              <strong>16 Apr 14:20</strong> · Quote received
              <div class="muted" style="font-size:12px">SAPlumb · R 8 200 incl VAT · valid 7 days · PDF attached</div>
            </div>
            <div style="padding:12px 14px;border-left:2px solid var(--ok);background:var(--ok-soft);border-radius:0 8px 8px 0;margin-bottom:10px">
              <strong>16 Apr 10:15</strong> · Triaged · SAPlumb assigned
              <div class="muted" style="font-size:12px">Sarah N. confirmed plumbing · high urgency · assigned to SAPlumb (historical geyser expertise on this property)</div>
            </div>
            <div style="padding:12px 14px;border-left:2px solid var(--ok);background:var(--ok-soft);border-radius:0 8px 8px 0">
              <strong>16 Apr 09:42</strong> · Ticket logged by K. Jacobs
              <div class="muted" style="font-size:12px">In-app · 3 photos · voice note 14s · urgency: high</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="tab === 'messages'" class="mt-pane active">
      <div style="padding:20px 32px">
        <div class="pcard">
          <h3><MessageCircle :size="14" />Ticket thread (tenant + supplier + owner + team · 8 msgs)</h3>

          <div style="margin-top:14px">
            <div style="font-size:11px;color:var(--muted);text-align:center;margin:8px 0">16 Apr · 09:42 · tenant · in-app</div>
            <div style="background:var(--paper);padding:10px 14px;border-radius:10px 10px 10px 2px;max-width:70%;font-size:13px">
              Hi there, geyser stopped heating overnight. Three photos attached. No hot water at all. [voice note]
            </div>

            <div style="font-size:11px;color:var(--muted);text-align:right;margin:8px 0">16 Apr · 10:15 · Sarah N · in-app</div>
            <div style="text-align:right">
              <div style="display:inline-block;background:var(--navy);color:#fff;padding:10px 14px;border-radius:10px 10px 2px 10px;max-width:70%;font-size:13px;text-align:left">
                Thanks K. — SAPlumb coming out today for assessment, quote by EOD. I'll keep you posted.
              </div>
            </div>

            <div style="font-size:11px;color:var(--muted);text-align:center;margin:8px 0">16 Apr · 14:25 · SAPlumb · supplier portal</div>
            <div style="background:#E4E4EE;padding:10px 14px;border-radius:10px 10px 10px 2px;max-width:70%;font-size:13px">
              <strong>SAPlumb</strong> · Quote uploaded · R 8 200 · 150L Kwikot + CoC + disposal · 5yr warranty. Recommend replace not repair (9yr old unit).
            </div>

            <div style="background:var(--warn-soft);border-left:3px solid var(--warn);padding:10px 14px;border-radius:6px;font-size:12px;margin:14px 0">
              <NotebookPen :size="12" style="display:inline;vertical-align:middle" /> <strong>Internal · Sarah N · 14:30</strong><br>
              Going to send to owner. Given no hot water I'll push for fast turnaround. If owner silent past 48h, emergency override under mandate clause 8.2.
            </div>

            <div style="font-size:11px;color:var(--muted);text-align:right;margin:8px 0">16 Apr · 14:35 · Sarah N → J. van der Merwe · email + WhatsApp</div>
            <div style="text-align:right">
              <div style="display:inline-block;background:var(--navy);color:#fff;padding:10px 14px;border-radius:10px 10px 2px 10px;max-width:70%;font-size:13px;text-align:left">
                J — geyser replacement needed at 22 Plein. Tenant has no hot water. Quote R 8 200 from SAPlumb. Please respond ASAP.
              </div>
            </div>

            <div style="font-size:11px;color:var(--muted);text-align:right;margin:8px 0">17 Apr · 09:00 · Sarah N → owner · reminder</div>
            <div style="text-align:right">
              <div style="display:inline-block;background:var(--warn-soft);color:var(--warn);padding:10px 14px;border-radius:10px 10px 2px 10px;max-width:70%;font-size:13px;text-align:left">
                Following up — 20h since the Gate 3 was sent. Please approve or call me. SLA breaches at 14:35 today.
              </div>
            </div>

            <div style="border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:20px">
              <textarea placeholder="Reply…" style="width:100%;border:none;outline:none;resize:none;font-family:inherit;font-size:13px;min-height:50px" />
              <div style="display:flex;align-items:center;gap:10px;padding-top:10px;border-top:1px solid var(--line);font-size:12px">
                <span style="color:var(--muted)">To:</span>
                <label><input type="radio" name="to"> Tenant</label>
                <label><input type="radio" name="to" checked> Owner</label>
                <label><input type="radio" name="to"> Supplier</label>
                <label><input type="radio" name="to"> Internal note</label>
                <button class="btn primary" style="margin-left:auto" aria-label="Send reply"><Send :size="14" />Send</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

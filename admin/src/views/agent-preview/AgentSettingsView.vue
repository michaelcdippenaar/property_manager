<!--
  AgentSettingsView — Agency settings (1:1 port)
  From docs/prototypes/admin-shell/index.html #route-settings.
-->
<script setup lang="ts">
import { ref } from 'vue'
import {
  Building2,
  Users,
  Percent,
  Landmark,
  Award,
  ShieldCheck,
  FileLock,
  Plug,
  Palette,
  Code,
  Info,
  CheckCircle2,
  AlertCircle,
} from 'lucide-vue-next'

interface NavItem { id: string; icon: unknown; label: string }
interface NavGroup { label: string; items: NavItem[] }

const groups: NavGroup[] = [
  {
    label: 'Agency',
    items: [
      { id: 'profile', icon: Building2, label: 'Profile' },
      { id: 'team', icon: Users, label: 'Team' },
      { id: 'fees', icon: Percent, label: 'Fees & commission' },
      { id: 'trust', icon: Landmark, label: 'Trust account' },
    ],
  },
  {
    label: 'Compliance',
    items: [
      { id: 'ffc', icon: Award, label: 'FFC & PPRA' },
      { id: 'popia', icon: ShieldCheck, label: 'POPIA / PAIA' },
      { id: 'retention', icon: FileLock, label: 'Retention rules' },
    ],
  },
  {
    label: 'Platform',
    items: [
      { id: 'integrations', icon: Plug, label: 'Integrations' },
      { id: 'branding', icon: Palette, label: 'Branding' },
      { id: 'api', icon: Code, label: 'API & webhooks' },
    ],
  },
]

const active = ref('profile')

interface Integration {
  letter: string
  name: string
  sub: string
  bg: string
  color: string
}

const integrations: Integration[] = [
  { letter: 'T', name: 'TransUnion', sub: 'Credit checks · 42 YTD', bg: 'var(--info-soft)', color: 'var(--info)' },
  { letter: 'W', name: 'WhatsApp Business', sub: 'Twilio · 318 msgs/mo', bg: 'var(--ok-soft)', color: 'var(--ok)' },
  { letter: 'A', name: 'ABSA Trust', sub: 'Bank feed · reconciled daily', bg: 'var(--navy-soft)', color: 'var(--navy)' },
  { letter: 'P', name: 'Property24', sub: 'Listing sync · 6 active', bg: 'var(--accent-soft)', color: 'var(--accent)' },
]
</script>

<template>
  <section class="route">
    <div class="page-header">
      <div class="breadcrumb"><span>Settings</span></div>
      <div class="page-header-row">
        <div>
          <h1>Settings</h1>
          <p class="sub">Agency profile · team · fee defaults · integrations · compliance.</p>
        </div>
      </div>
    </div>

    <div class="settings-wrap">
      <div class="settings-nav">
        <template v-for="(g, gi) in groups" :key="g.label">
          <div class="settings-group-label" :style="gi > 0 ? 'margin-top:10px' : ''">{{ g.label }}</div>
          <button
            v-for="item in g.items"
            :key="item.id"
            class="nav-item"
            :class="{ active: active === item.id }"
            style="border-radius:0;margin:0;padding:10px 16px"
            @click="active = item.id"
          >
            <component :is="item.icon" :size="18" />{{ item.label }}
          </button>
        </template>
      </div>
      <div class="settings-panel">
        <h2 style="margin-bottom:4px">Winelands Property Co.</h2>
        <p class="sub" style="margin-bottom:20px;color:var(--muted)">Active since 2024 · 7-step onboarding complete · FFC valid to 31 Oct 2026</p>

        <div class="pcard" style="margin-bottom:14px">
          <h3><Info :size="14" />Agency profile</h3>
          <dl class="kv">
            <dt>Trading name</dt><dd>Winelands Property Co.</dd>
            <dt>Legal entity</dt><dd>Winelands Realty (Pty) Ltd · 2019/114883/07</dd>
            <dt>VAT number</dt><dd>4150278822</dd>
            <dt>Principal agent</dt><dd>MC Dippenaar · FFC WCPR-22491</dd>
            <dt>PPRA registration</dt><dd>PPRA-2024-117288</dd>
            <dt>Registered office</dt><dd>Unit 3, De Zicht, Stellenbosch 7600</dd>
          </dl>
        </div>

        <div class="pcard" style="margin-bottom:14px">
          <h3><ShieldCheck :size="14" />Compliance status</h3>
          <div class="compliance-grid">
            <div style="display:flex;align-items:center;gap:6px"><CheckCircle2 :size="13" style="color:var(--ok);flex-shrink:0" /> <strong>FFC</strong> · valid to 31 Oct 2026</div>
            <div style="display:flex;align-items:center;gap:6px"><CheckCircle2 :size="13" style="color:var(--ok);flex-shrink:0" /> <strong>PAIA Manual</strong> · lodged 14 Feb 2025</div>
            <div style="display:flex;align-items:center;gap:6px"><CheckCircle2 :size="13" style="color:var(--ok);flex-shrink:0" /> <strong>Information Officer</strong> · registered</div>
            <div style="display:flex;align-items:center;gap:6px"><CheckCircle2 :size="13" style="color:var(--ok);flex-shrink:0" /> <strong>FICA Risk Programme</strong> · signed</div>
            <div style="display:flex;align-items:center;gap:6px"><CheckCircle2 :size="13" style="color:var(--ok);flex-shrink:0" /> <strong>Trust account</strong> · ABSA-4412</div>
            <div style="display:flex;align-items:center;gap:6px"><AlertCircle :size="13" style="color:var(--warn);flex-shrink:0" /> <strong>Annual audit</strong> · due 31 May</div>
          </div>
        </div>

        <div class="pcard">
          <h3><Plug :size="14" />Integrations</h3>
          <div class="integrations-grid">
            <div v-for="i in integrations" :key="i.name" class="integration-cell">
              <div class="integration-logo" :style="`background:${i.bg};color:${i.color}`">{{ i.letter }}</div>
              <div>
                <div style="font-weight:500">{{ i.name }}</div>
                <div class="muted" style="font-size:11px">{{ i.sub }}</div>
              </div>
              <CheckCircle2 :size="14" style="margin-left:auto;color:var(--ok)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style>
.agent-shell .settings-wrap {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 0;
  padding: 20px 32px;
  min-height: 500px;
}
.agent-shell .settings-nav {
  border: 1px solid var(--line);
  border-right: none;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  background: #fff;
  padding: 10px 0;
}
.agent-shell .settings-group-label {
  padding: 8px 16px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  font-weight: 600;
}
.agent-shell .settings-panel {
  border: 1px solid var(--line);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  background: #fff;
  padding: 24px 28px;
}
.agent-shell .compliance-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  font-size: 13px;
}
.agent-shell .integrations-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  font-size: 13px;
}
.agent-shell .integration-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.agent-shell .integration-logo {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
</style>

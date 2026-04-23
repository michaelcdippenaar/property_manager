<template>
  <div>
    <PageHeader
      title="DevOps Console"
      subtitle="Build commands, environment health, and developer tools"
      :crumbs="[{ label: 'Admin', to: '/admin/users' }, { label: 'DevOps Console' }]"
    />

    <!-- ── 1. Mobile Builds ─────────────────────────────────────────────────── -->
    <section class="card overflow-hidden mb-6">
      <!-- Card header -->
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100">
        <Smartphone :size="14" :stroke-width="1.75" class="text-gray-400 flex-shrink-0" />
        <h2 class="text-sm font-semibold text-gray-800">Mobile Builds</h2>
        <span class="ml-auto text-xs text-gray-400">Quasar + Capacitor</span>
      </div>

      <div class="px-5 pt-4 pb-5">
        <!-- Environment tabs -->
        <div class="flex items-center gap-1 mb-5 border-b border-gray-100 -mx-5 px-5">
          <button
            v-for="env in environments"
            :key="env.key"
            class="relative pb-3 px-1 mr-3 text-sm font-medium transition-colors"
            :class="selectedEnv === env.key
              ? 'text-navy'
              : 'text-gray-500 hover:text-gray-700'"
            @click="selectedEnv = env.key"
          >
            {{ env.label }}
            <span
              v-if="selectedEnv === env.key"
              class="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-navy"
            />
          </button>
        </div>

        <!-- App cards -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div
            v-for="app in apps"
            :key="app.key"
            class="rounded-xl border border-gray-200 bg-gray-50/50 overflow-hidden"
          >
            <!-- App header -->
            <div class="flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-white">
              <div class="w-8 h-8 rounded-lg bg-navy/8 flex items-center justify-center flex-shrink-0">
                <Layers :size="16" :stroke-width="1.75" class="text-navy" />
              </div>
              <div>
                <div class="text-sm font-semibold text-gray-900">{{ app.label }}</div>
                <div class="text-xs text-gray-500">{{ app.description }}</div>
              </div>
            </div>

            <div class="p-4 space-y-3">
              <!-- iOS build -->
              <CommandRow
                :id="`${app.key}-${selectedEnv}-ios`"
                platform="iOS"
                :command="buildCommand(app.key, selectedEnv, 'ios')"
                :copied="copied[`${app.key}-${selectedEnv}-ios`] ?? false"
                @copy="copyCommand(`${app.key}-${selectedEnv}-ios`, buildCommand(app.key, selectedEnv, 'ios'))"
              />

              <!-- Android build -->
              <CommandRow
                :id="`${app.key}-${selectedEnv}-android`"
                platform="Android"
                :command="buildCommand(app.key, selectedEnv, 'android')"
                :copied="copied[`${app.key}-${selectedEnv}-android`] ?? false"
                @copy="copyCommand(`${app.key}-${selectedEnv}-android`, buildCommand(app.key, selectedEnv, 'android'))"
              />

              <!-- Live-reload (dev only) -->
              <template v-if="selectedEnv === 'development'">
                <div class="my-1 border-t border-dashed border-gray-200" />
                <CommandRow
                  :id="`${app.key}-dev-livereload`"
                  platform="Live Reload"
                  variant="accent"
                  :command="liveReloadCommand(app.key)"
                  :copied="copied[`${app.key}-dev-livereload`] ?? false"
                  @copy="copyCommand(`${app.key}-dev-livereload`, liveReloadCommand(app.key))"
                />
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── 2. Environments ──────────────────────────────────────────────────── -->
    <section class="card overflow-hidden mb-6">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100">
        <Server :size="14" :stroke-width="1.75" class="text-gray-400 flex-shrink-0" />
        <h2 class="text-sm font-semibold text-gray-800">Environments</h2>
        <span class="ml-auto text-xs text-gray-400">API health</span>
      </div>

      <div class="divide-y divide-gray-100">
        <div
          v-for="env in environments"
          :key="env.key"
          class="flex items-center gap-4 px-5 py-4"
        >
          <!-- Status dot -->
          <span
            class="w-2.5 h-2.5 rounded-full flex-shrink-0 transition-colors"
            :class="pingResults[env.key]
              ? (pingResults[env.key].ok ? 'bg-success-500' : 'bg-danger-600')
              : 'bg-gray-300'"
          />

          <!-- Name + badge -->
          <div class="w-32 flex-shrink-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-gray-900">{{ env.label }}</span>
              <span
                class="inline-flex items-center px-1.5 py-0.5 rounded-md text-xs font-semibold"
                :class="env.badgeClass"
              >{{ env.key }}</span>
            </div>
          </div>

          <!-- API URL -->
          <code class="flex-1 min-w-0 text-xs text-gray-500 font-mono truncate bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
            {{ env.apiUrl }}
          </code>

          <!-- Ping result -->
          <div class="w-28 flex-shrink-0 text-right">
            <template v-if="pingResults[env.key]">
              <span
                class="text-sm font-medium"
                :class="pingResults[env.key].ok ? 'text-success-600' : 'text-danger-600'"
              >
                {{ pingResults[env.key].ok ? pingResults[env.key].ms + ' ms' : 'Error' }}
              </span>
            </template>
            <span v-else class="text-xs text-gray-400">Not pinged</span>
          </div>

          <!-- Ping button -->
          <button
            class="btn btn-secondary flex items-center gap-1.5 flex-shrink-0 min-w-[88px]"
            :disabled="pingResults[env.key]?.loading"
            @click="pingEnv(env.key)"
          >
            <template v-if="pingResults[env.key]?.loading">
              <Loader :size="14" :stroke-width="1.75" class="animate-spin" />
              <span>Pinging</span>
            </template>
            <template v-else>
              <Zap :size="14" :stroke-width="1.75" />
              <span>Ping</span>
            </template>
          </button>
        </div>
      </div>
    </section>

    <!-- ── 3. Quick Links ───────────────────────────────────────────────────── -->
    <section class="card overflow-hidden">
      <div class="flex items-center gap-2.5 px-5 py-3.5 border-b border-gray-100">
        <ExternalLink :size="14" :stroke-width="1.75" class="text-gray-400 flex-shrink-0" />
        <h2 class="text-sm font-semibold text-gray-800">Quick Links</h2>
      </div>

      <div class="p-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <template v-for="link in quickLinks" :key="link.label">
          <a
            v-if="link.href"
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="group flex flex-col items-center gap-3 p-4 rounded-xl border border-gray-200 bg-gray-50/50 hover:bg-white hover:border-navy/20 hover:shadow-soft transition-all"
          >
            <div class="w-10 h-10 rounded-xl bg-navy/8 flex items-center justify-center group-hover:bg-navy/12 transition-colors">
              <component :is="link.icon" :size="20" :stroke-width="1.75" class="text-navy" />
            </div>
            <div class="text-center">
              <div class="text-sm font-semibold text-gray-900 group-hover:text-navy transition-colors">{{ link.label }}</div>
              <div class="text-xs text-gray-500 mt-0.5">{{ link.description }}</div>
            </div>
          </a>
          <RouterLink
            v-else
            :to="link.to!"
            class="group flex flex-col items-center gap-3 p-4 rounded-xl border border-gray-200 bg-gray-50/50 hover:bg-white hover:border-navy/20 hover:shadow-soft transition-all"
          >
            <div class="w-10 h-10 rounded-xl bg-navy/8 flex items-center justify-center group-hover:bg-navy/12 transition-colors">
              <component :is="link.icon" :size="20" :stroke-width="1.75" class="text-navy" />
            </div>
            <div class="text-center">
              <div class="text-sm font-semibold text-gray-900 group-hover:text-navy transition-colors">{{ link.label }}</div>
              <div class="text-xs text-gray-500 mt-0.5">{{ link.description }}</div>
            </div>
          </RouterLink>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, h, defineComponent } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Smartphone, Layers, Server, Zap, Loader, ExternalLink,
  FlaskConical, Activity, Users, Settings, Copy, Check, BarChart2,
} from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import api from '../../api'

// ── Types ─────────────────────────────────────────────────────────────────────

type EnvKey = 'development' | 'staging' | 'production'
type Platform = 'ios' | 'android'

interface Environment {
  key: EnvKey
  label: string
  apiUrl: string
  badgeClass: string
}

interface AppDef {
  key: string
  label: string
  description: string
}

// ── CommandRow inline component ───────────────────────────────────────────────

const CommandRow = defineComponent({
  name: 'CommandRow',
  props: {
    id: { type: String, required: true },
    platform: { type: String, required: true },
    command: { type: String, required: true },
    copied: { type: Boolean, default: false },
    variant: { type: String, default: 'default' }, // 'default' | 'accent'
  },
  emits: ['copy'],
  setup(props, { emit }) {
    return () => {
      const isAccent = props.variant === 'accent'
      return h('div', { class: 'flex items-start gap-2' }, [
        // Platform label
        h('span', {
          class: [
            'flex-shrink-0 mt-0.5 inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold min-w-[72px] justify-center',
            isAccent ? 'bg-accent/10 text-accent' : 'bg-gray-100 text-gray-600',
          ].join(' '),
        }, props.platform),
        // Command code
        h('code', {
          class: 'flex-1 min-w-0 text-xs font-mono text-gray-600 bg-gray-50 border border-gray-100 rounded-md px-2.5 py-1.5 leading-relaxed break-all',
        }, props.command),
        // Copy button
        h('button', {
          class: [
            'flex-shrink-0 p-1.5 rounded-lg border transition-colors mt-0.5',
            props.copied
              ? 'bg-success-50 border-success-200 text-success-600'
              : 'bg-white border-gray-200 text-gray-400 hover:text-gray-700 hover:border-gray-300',
          ].join(' '),
          title: props.copied ? 'Copied!' : 'Copy command',
          onClick: () => emit('copy'),
        }, [
          h(props.copied ? Check : Copy, { size: 13, strokeWidth: 1.75 }),
        ]),
      ])
    }
  },
})

// ── State ─────────────────────────────────────────────────────────────────────

const selectedEnv = ref<EnvKey>('staging')
const copied = ref<Record<string, boolean>>({})
const pingResults = ref<Record<string, { ms: number; ok: boolean; loading: boolean }>>({})

// ── Data ──────────────────────────────────────────────────────────────────────

const environments: Environment[] = [
  {
    key: 'development',
    label: 'Development',
    apiUrl: 'http://localhost:8000/api/v1',
    badgeClass: 'bg-gray-100 text-gray-600',
  },
  {
    key: 'staging',
    label: 'Staging',
    apiUrl: 'https://backend.klikk.co.za/api/v1',
    badgeClass: 'bg-warning-50 text-warning-700',
  },
  {
    key: 'production',
    label: 'Production',
    apiUrl: 'https://api.klikk.co.za/api/v1',
    badgeClass: 'bg-success-50 text-success-700',
  },
]

const apps: AppDef[] = [
  {
    key: 'agent-app',
    label: 'Agent App',
    description: 'Quasar Capacitor — agents & property managers',
  },
  {
    key: 'tenant-app',
    label: 'Tenant App',
    description: 'Quasar Capacitor — tenants & residents',
  },
]

const quickLinks: { label: string; description: string; icon: unknown; to?: string; href?: string }[] = [
  { to: '/testing', icon: FlaskConical, label: 'Testing Portal', description: 'Run E2E test suites' },
  { to: '/property-info/monitor', icon: Activity, label: 'Agent Monitor', description: 'Live AI agent logs' },
  { to: '/admin/users', icon: Users, label: 'Users', description: 'Manage platform users' },
  { to: '/admin/agency', icon: Settings, label: 'Agency Settings', description: 'Configure agency' },
  { href: 'https://analytics.klikk.co.za', icon: BarChart2, label: 'Analytics', description: 'Plausible site analytics' },
]

// ── Command builders ──────────────────────────────────────────────────────────

const BASE = '/Users/mcdippenaar/PycharmProjects/tremly_property_manager'

function buildCommand(appKey: string, env: EnvKey, platform: Platform): string {
  const dir = `${BASE}/${appKey}`
  const modeFlag = env !== 'development' ? ` --mode ${env}` : ''
  const ideFlag = platform === 'ios' ? ' --ide' : ''
  return `cd ${dir} && LANG=en_US.UTF-8 npx quasar build -m capacitor -T ${platform}${modeFlag}${ideFlag}`
}

function liveReloadCommand(appKey: string): string {
  return `cd ${BASE}/${appKey} && LANG=en_US.UTF-8 npx quasar dev -m capacitor -T ios`
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function copyCommand(id: string, text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value[id] = true
    setTimeout(() => { copied.value[id] = false }, 2000)
  } catch {
    // Clipboard unavailable in non-secure context
  }
}

async function pingEnv(envKey: string) {
  const env = environments.find(e => e.key === envKey)
  if (!env) return

  pingResults.value[envKey] = { ms: 0, ok: false, loading: true }
  const start = Date.now()
  try {
    if (envKey === 'development') {
      await api.get('/health/')
    } else {
      // Use no-cors for cross-origin envs — we only care about reachability
      const baseUrl = env.apiUrl.replace('/api/v1', '')
      await fetch(`${baseUrl}/health/`, { method: 'GET', mode: 'no-cors' })
    }
    pingResults.value[envKey] = { ms: Date.now() - start, ok: true, loading: false }
  } catch {
    pingResults.value[envKey] = { ms: Date.now() - start, ok: false, loading: false }
  }
}
</script>

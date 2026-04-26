<template>
  <div class="max-w-3xl mx-auto">
    <PageHeader
      title="Billing &amp; Plan"
      subtitle="Your current plan, usage metrics, and upgrade options."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Settings' }, { label: 'Billing' }]"
    >
      <template #title-adornment>
        <CreditCard :size="20" class="text-navy" />
      </template>
    </PageHeader>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center gap-2 text-sm text-gray-400 py-12 justify-center">
      <Loader2 :size="15" class="animate-spin" />
      Loading plan info...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {{ error }}
    </div>

    <template v-else-if="billingInfo">

      <!-- Current plan card -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden mb-6">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Sparkles :size="14" class="text-navy" />
            Current Plan
          </h2>
        </div>
        <div class="px-5 py-5 flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-bold text-gray-900">
                {{ billingInfo.tier?.name ?? 'Pro' }}
              </span>
              <span
                v-if="billingInfo.tier?.price_monthly === 0"
                class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
              >
                Free
              </span>
              <span
                v-else-if="billingInfo.tier?.price_monthly"
                class="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-medium text-navy"
              >
                R{{ billingInfo.tier.price_monthly.toLocaleString('en-ZA') }}/month
              </span>
            </div>
            <p class="mt-1 text-sm text-gray-500">
              Billed monthly &middot; Excl. VAT
            </p>
          </div>
          <a
            :href="billingInfo.upgrade_url"
            target="_blank"
            rel="noopener"
            class="flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent/90 transition-colors"
          >
            <ArrowUpRight :size="14" />
            Upgrade Plan
          </a>
        </div>

        <!-- Feature list -->
        <div
          v-if="billingInfo.tier?.features"
          class="border-t border-gray-100 px-5 py-4 grid grid-cols-2 gap-x-8 gap-y-2"
        >
          <div
            v-for="(enabled, slug) in billingInfo.tier.features"
            :key="slug"
            class="flex items-center gap-2 text-sm"
          >
            <CheckCircle2 v-if="enabled" :size="14" class="text-green-500 shrink-0" />
            <XCircle v-else :size="14" class="text-gray-300 shrink-0" />
            <span :class="enabled ? 'text-gray-700' : 'text-gray-400'">
              {{ FEATURE_LABELS[slug as FeatureSlug] ?? slug }}
            </span>
          </div>
        </div>
      </section>

      <!-- Usage quotas -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden mb-6">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <BarChart2 :size="14" class="text-navy" />
            Usage
          </h2>
        </div>
        <div class="px-5 py-5 space-y-5">
          <div
            v-for="quota in billingInfo.quotas"
            :key="quota.key"
            class="space-y-1.5"
          >
            <div class="flex items-center justify-between text-sm">
              <span class="font-medium text-gray-700">
                {{ QUOTA_LABELS[quota.key] ?? quota.key }}
              </span>
              <span :class="quota.blocked ? 'text-red-600 font-semibold' : quota.warning ? 'text-amber-600 font-medium' : 'text-gray-500'">
                <template v-if="quota.unlimited">Unlimited</template>
                <template v-else>
                  {{ quota.used }} / {{ quota.limit }}
                  <span v-if="quota.warning && !quota.blocked" class="ml-1 text-xs">(warning)</span>
                  <span v-if="quota.blocked" class="ml-1 text-xs">(limit reached)</span>
                </template>
              </span>
            </div>
            <div v-if="!quota.unlimited" class="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="quota.blocked ? 'bg-red-500' : quota.warning ? 'bg-amber-400' : 'bg-navy'"
                :style="{ width: `${Math.min((quota.fraction ?? 0) * 100, 100)}%` }"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- All tiers comparison -->
      <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden mb-6">
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Layers :size="14" class="text-navy" />
            Available Plans
          </h2>
        </div>
        <div class="px-5 py-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div
            v-for="t in billingInfo.all_tiers"
            :key="t.slug"
            class="rounded-xl border p-4 flex flex-col gap-2 relative"
            :class="[
              t.slug === billingInfo.tier?.slug
                ? 'border-navy/40 bg-navy/5 ring-1 ring-navy/20'
                : 'border-gray-200',
              t.highlight ? 'shadow-sm' : '',
            ]"
          >
            <span
              v-if="t.slug === billingInfo.tier?.slug"
              class="absolute top-2 right-2 rounded-full bg-navy px-1.5 py-0.5 text-[11px] font-semibold text-white"
            >
              Current
            </span>
            <p class="text-sm font-semibold text-gray-800">{{ t.name }}</p>
            <p class="text-xs text-gray-500">{{ t.price_label }}</p>
          </div>
        </div>
      </section>

      <!-- Admin tier assignment (admins only) -->
      <section
        v-if="isAdmin"
        class="rounded-2xl border border-gray-200 bg-white overflow-hidden"
      >
        <div class="px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <ShieldCheck :size="14" class="text-navy" />
            Admin: Assign Tier
          </h2>
        </div>
        <div class="px-5 py-5 flex items-end gap-4">
          <div class="flex-1">
            <label class="label">Subscription tier</label>
            <select v-model="newTierSlug" class="input">
              <option v-for="t in billingInfo.all_tiers" :key="t.slug" :value="t.slug">
                {{ t.name }}
              </option>
            </select>
          </div>
          <button
            type="button"
            :disabled="saving || newTierSlug === billingInfo.tier?.slug"
            class="rounded-xl bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:bg-navy/90 transition-colors"
            @click="assignTier"
          >
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            <span v-else>Save</span>
          </button>
        </div>
        <p class="px-5 pb-4 text-xs text-gray-400">
          v1.0: tier assignment is manual. Self-serve Stripe billing is coming soon.
        </p>
      </section>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  CreditCard, Loader2, Sparkles, ArrowUpRight,
  CheckCircle2, XCircle, BarChart2, Layers, ShieldCheck,
} from 'lucide-vue-next'
import api from '../../api'
import { useToast } from '../../composables/useToast'
import { useAuthStore } from '../../stores/auth'
import { useTier } from '../../composables/useTier'
import PageHeader from '../../components/PageHeader.vue'

const auth = useAuthStore()
const { showToast } = useToast()
const { billingInfo, isLoading, error, refresh } = useTier()

const saving = ref(false)
const newTierSlug = ref<string | null>(null)

const isAdmin = computed(
  () => auth.user?.role === 'admin' || auth.user?.role === 'agency_admin'
)

type FeatureSlug =
  | 'ai_lease_generation'
  | 'ai_chat'
  | 'e_signing'
  | 'api_access'
  | 'mcp_access'
  | 'owner_portal'
  | 'tenant_portal'
  | 'supplier_portal'
  | 'multiple_users'

const FEATURE_LABELS: Record<FeatureSlug, string> = {
  ai_lease_generation: 'AI Lease Generation',
  ai_chat: 'AI Tenant Chat',
  e_signing: 'Native E-Signing',
  api_access: 'REST API Access',
  mcp_access: 'MCP Server Access',
  owner_portal: 'Owner Portal',
  tenant_portal: 'Tenant Portal',
  supplier_portal: 'Supplier Portal',
  multiple_users: 'Multiple Users',
}

const QUOTA_LABELS: Record<string, string> = {
  properties: 'Properties',
  units: 'Units',
  users: 'Users',
  ai_contracts_yearly: 'AI Contracts (this year)',
}

async function assignTier() {
  if (!newTierSlug.value || saving.value) return
  saving.value = true
  try {
    await api.patch('/auth/agency/billing/', { subscription_tier: newTierSlug.value })
    await refresh()
    showToast('Plan updated', 'success')
  } catch (err: any) {
    showToast(err?.response?.data?.detail ?? 'Failed to update plan', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await refresh()
  newTierSlug.value = billingInfo.value?.tier?.slug ?? null
})
</script>

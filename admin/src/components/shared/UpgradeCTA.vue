<!--
  UpgradeCTA — shown in place of a gated feature when the current tier does not
  include it.  Replaces a raw 402/403 error with a friendly "Upgrade" prompt.

  Usage:
    <UpgradeCTA
      v-if="!hasFeature('ai_lease_generation')"
      feature="ai_lease_generation"
      label="AI Lease Generation"
    />
-->
<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles, ArrowUpRight } from 'lucide-vue-next'
import { useTier } from '../../composables/useTier'

interface Props {
  /** The feature slug — used to look up gating info. */
  feature: string
  /** Human-readable feature name shown in the card. */
  label?: string
  /** Description override. Defaults to a generic upgrade prompt. */
  description?: string
  /** Size variant: 'full' (takes full card slot) | 'inline' (slim bar). */
  variant?: 'full' | 'inline'
}

const props = withDefaults(defineProps<Props>(), {
  label: 'This feature',
  description: '',
  variant: 'full',
})

const { upgradeUrl, tierName } = useTier()

const desc = computed(
  () =>
    props.description ||
    `${props.label} is not included in your current ${tierName.value} plan. Upgrade to unlock it.`
)
</script>

<template>
  <!-- Inline bar variant -->
  <div
    v-if="variant === 'inline'"
    class="flex items-center gap-3 rounded-xl border border-accent/20 bg-accent/5 px-4 py-3"
  >
    <Sparkles :size="16" class="shrink-0 text-accent" />
    <p class="text-sm text-gray-700 grow">
      <span class="font-medium text-accent">{{ label }}</span>
      requires an upgraded plan.
    </p>
    <a
      :href="upgradeUrl"
      target="_blank"
      rel="noopener"
      class="ml-auto flex items-center gap-1 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent/90 transition-colors"
    >
      Upgrade
      <ArrowUpRight :size="12" />
    </a>
  </div>

  <!-- Full card variant -->
  <div
    v-else
    class="flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-accent/30 bg-accent/5 p-10 text-center"
  >
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10">
      <Sparkles :size="22" class="text-accent" />
    </div>
    <div>
      <p class="text-base font-semibold text-gray-800">{{ label }}</p>
      <p class="mt-1 max-w-sm text-sm text-gray-500">{{ desc }}</p>
    </div>
    <a
      :href="upgradeUrl"
      target="_blank"
      rel="noopener"
      class="flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-accent/90 transition-colors"
    >
      <ArrowUpRight :size="15" />
      Upgrade Plan
    </a>
  </div>
</template>

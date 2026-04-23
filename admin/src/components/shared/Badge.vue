<!--
  Badge — status pill / tag

  Consolidates the 6+ badge implementations across admin-shell and the
  agent prototypes (.badge.active/signing/vacant/…, .when-pill.overdue/today/…,
  .urgency-chip, .role-pill, .portal-chip) into one component.

  Usage:
    <Badge tone="active" dot>Active</Badge>
    <Badge tone="signing" size="sm">Signing</Badge>
    <Badge tone="gate">Gate 3</Badge>
-->
<script setup lang="ts">
type Tone =
  | 'neutral'
  | 'active'
  | 'signing'
  | 'vacant'
  | 'renewal'
  | 'refund'
  | 'marketing'
  | 'moveout'
  | 'applied'
  | 'ok'
  | 'warn'
  | 'danger'
  | 'info'
  | 'gate'

interface Props {
  tone?: Tone
  /** Show a leading filled dot in the current colour */
  dot?: boolean
  size?: 'md' | 'sm'
}

withDefaults(defineProps<Props>(), {
  tone: 'neutral',
  dot: false,
  size: 'md',
})
</script>

<template>
  <span
    class="klikk-badge"
    :class="[
      tone !== 'neutral' ? `tone-${tone}` : '',
      size === 'sm' ? 'size-sm' : '',
    ]"
  >
    <span v-if="dot" class="dot" />
    <slot />
  </span>
</template>

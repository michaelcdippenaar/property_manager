<!--
  AlertStrip — inline banner for urgent information or SLA warnings

  Replaces .alert-strip (admin-shell), .urgent-banner (agent-dashboard),
  .alerts (agent-timeline), .emrg-hero (agent-mobile) — same pattern,
  four names.

  Usage:
    <AlertStrip tone="warn">
      <strong>1 Gate 3 awaiting owner decision</strong> · 22 Plein geyser
      <template #action>
        <button class="btn-sm">Review & chase</button>
      </template>
    </AlertStrip>

    <AlertStrip tone="danger" pulse>System outage — retrying…</AlertStrip>
-->
<script setup lang="ts">
interface Props {
  tone?: 'info' | 'ok' | 'warn' | 'danger'
  pulse?: boolean
}

withDefaults(defineProps<Props>(), {
  tone: 'warn',
  pulse: false,
})
</script>

<template>
  <div
    class="klikk-alert-strip"
    :class="[
      `tone-${tone}`,
      pulse ? 'pulse' : '',
    ]"
  >
    <span class="body"><slot /></span>
    <span v-if="$slots.action" class="action">
      <slot name="action" />
    </span>
  </div>
</template>

<style scoped>
.body {
  flex: 1;
  min-width: 0;
}
.action {
  margin-left: auto;
  flex-shrink: 0;
}
</style>

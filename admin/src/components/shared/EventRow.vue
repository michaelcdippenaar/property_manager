<!--
  EventRow — one row in the Action Queue

  Admin-shell and agent-events prototype already use identical class names
  (.ev-row, .ev-when.overdue/today/soon/future, .ev-act), so this component
  lifts the pattern wholesale for reuse across Dashboard + Property god-view
  + any future event surface.

  Usage:
    <EventRow
      when="2d overdue"
      tone="overdue"
      addr="15 Andringa"
      ctx="Rent overdue · R 12 800"
      action="Chase tenant"
      @action="handleChase"
    />
-->
<script setup lang="ts">
interface Props {
  /** Pill text — e.g. "Today", "2d overdue", "Fri 19 Apr" */
  when: string
  /** Pill colour */
  tone?: 'overdue' | 'today' | 'soon' | 'future'
  /** Primary line — property address or entity name */
  addr: string
  /** Secondary line — what's happening / why this event is surfaced */
  ctx?: string
  /** Action button label. Emits 'action' on click. */
  action?: string
  /** Primary visual emphasis on the action button */
  primary?: boolean
}

withDefaults(defineProps<Props>(), {
  tone: 'future',
  ctx: '',
  action: '',
  primary: false,
})

defineEmits<{ (e: 'action'): void; (e: 'click'): void }>()
</script>

<template>
  <div class="klikk-ev-row" @click="$emit('click')">
    <span class="klikk-ev-when" :class="tone">{{ when }}</span>
    <div class="klikk-ev-body">
      <div class="klikk-ev-addr">{{ addr }}</div>
      <div v-if="ctx" class="klikk-ev-ctx">{{ ctx }}</div>
    </div>
    <button
      v-if="action"
      class="klikk-ev-act"
      :class="{ primary }"
      @click.stop="$emit('action')"
    >
      {{ action }}
    </button>
  </div>
</template>

<!--
  StatTile — KPI card

  Replaces the mockup's `.stat` primitive and the three-way naming drift
  between admin-shell (`.stat`), agent-dashboard (`.kpi`), and timeline
  views (`.stat .l/.v`) with a single component.

  Usage:
    <StatTile label="Open tickets" value="12" delta="4 new · 3 quoted" />
    <StatTile label="Gate 3 waiting" value="1" delta="owner silent 25h" tone="down" />
    <StatTile label="Avg close time" :value="4.2" suffix="d" delta="within SLA" tone="up" />
-->
<script setup lang="ts">
interface Props {
  label: string
  value: string | number
  /** Appended to value (e.g. "d", "%", "R") */
  suffix?: string
  /** Subtitle line under the value */
  delta?: string
  /** Visual tone for the delta line */
  tone?: 'neutral' | 'up' | 'down' | 'warn' | 'danger'
  /** Override value colour (for Gate warnings etc.) */
  valueColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  tone: 'neutral',
  suffix: '',
  delta: '',
  valueColor: '',
})

const deltaClass = () => {
  switch (props.tone) {
    case 'up': return 'up'
    case 'down': case 'danger': return 'down'
    default: return ''
  }
}
</script>

<template>
  <div class="klikk-stat">
    <div class="label">{{ label }}</div>
    <div class="value" :style="valueColor ? { color: valueColor } : undefined">
      {{ value }}<span v-if="suffix" class="suffix">{{ suffix }}</span>
    </div>
    <div v-if="delta" class="delta" :class="deltaClass()">{{ delta }}</div>
  </div>
</template>

<style scoped>
.suffix {
  font-size: 0.6em;
  font-weight: 500;
  color: #6B6B7A;
  margin-left: 2px;
}
</style>

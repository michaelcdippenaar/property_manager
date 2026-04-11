<template>
  <div class="card lg:col-span-3 overflow-hidden">
    <!-- Header -->
    <div class="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
      <h2 class="text-sm font-semibold text-gray-800">Lease timeline</h2>
      <RouterLink to="/leases/calendar" class="text-xs text-navy hover:underline">View calendar →</RouterLink>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="p-5 space-y-3 animate-pulse">
      <div v-for="i in 5" :key="i" class="flex gap-3">
        <div class="h-4 bg-gray-100 rounded flex-1"></div>
        <div class="h-4 bg-gray-100 rounded w-20"></div>
        <div class="h-4 bg-gray-100 rounded w-16"></div>
        <div class="h-4 bg-gray-100 rounded w-14"></div>
      </div>
    </div>

    <!-- Table -->
    <div v-else-if="timelineRows.length" class="table-scroll">
      <table class="table-wrap">
        <thead>
          <tr>
            <th scope="col">Property / Unit</th>
            <th scope="col">Lease ends</th>
            <th scope="col">Status</th>
            <th scope="col"><span class="sr-only">Action</span></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="row in displayRows" :key="row.key">
            <!-- Property group header (multi-unit) -->
            <tr v-if="row.isHeader" class="bg-gray-50/60">
              <td colspan="5" class="!py-2">
                <span class="flex items-center gap-1.5 text-xs font-semibold text-gray-600">
                  <Building2 :size="12" class="text-gray-400" />
                  {{ row.propertyName }}
                </span>
              </td>
            </tr>
            <!-- Unit / single-property row -->
            <tr v-else class="cursor-pointer" @click="$router.push(`/properties/${row.propertyId}`)">
              <td>
                <div class="flex items-center gap-1 text-xs text-gray-700">
                  <span v-if="row.indented" class="text-gray-300">└</span>
                  <span class="font-medium">{{ row.label }}</span>
                </div>
              </td>
              <td class="text-xs text-gray-500 tabular-nums">{{ row.endDateFormatted ?? '—' }}</td>
              <td><span :class="row.badgeClass">{{ row.badgeText }}</span></td>
              <td class="text-right">
                <RouterLink
                  :to="row.actionTo"
                  class="text-xs text-navy hover:underline inline-flex items-center gap-1"
                  :aria-label="row.actionLabel + ' for ' + row.label"
                  @click.stop
                >
                  <component :is="row.actionIcon" :size="12" />
                  <span class="hidden sm:inline">{{ row.actionLabel }}</span>
                </RouterLink>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <!-- Overflow indicator -->
      <div v-if="overflowCount > 0" class="px-5 py-2.5 border-t border-gray-100 text-center">
        <RouterLink to="/properties" class="text-xs text-navy hover:underline">
          and {{ overflowCount }} more unit{{ overflowCount > 1 ? 's' : '' }} →
        </RouterLink>
      </div>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else
      title="No properties"
      description="Add a property to see lease timelines."
      :icon="Building2"
    >
      <RouterLink to="/properties" class="btn-primary btn-sm">Add property</RouterLink>
    </EmptyState>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Building2, FilePlus2, RefreshCw } from 'lucide-vue-next'
import EmptyState from '../../components/EmptyState.vue'
import type { Property } from '../../types/property'
import type { Component } from 'vue'

const MAX_UNIT_ROWS = 8

const props = defineProps<{
  properties: Property[]
  loading: boolean
}>()

interface TimelineRow {
  key: string
  isHeader: boolean
  indented: boolean
  propertyId: number
  propertyName: string
  label: string
  tenantName: string | null
  endDateFormatted: string | null
  daysRemaining: number | null // null = vacant
  badgeClass: string
  badgeText: string
  actionTo: string
  actionLabel: string
  actionIcon: Component
}

function daysBetween(iso: string): number {
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-ZA', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function badge(days: number | null): { cls: string; text: string } {
  if (days === null) return { cls: 'badge-gray', text: 'Vacant' }
  if (days < 0) return { cls: 'badge-red', text: 'Expired' }
  if (days < 30) return { cls: 'badge-red', text: `${days}d` }
  if (days <= 90) return { cls: 'badge-amber', text: `${days}d` }
  return { cls: 'badge-green', text: `${days}d` }
}

function urgency(days: number | null): number {
  if (days !== null && days < 0) return 0   // expired — most urgent
  if (days === null) return 1               // vacant
  return 2 + days                           // lower days = more urgent
}

const timelineRows = computed<TimelineRow[]>(() => {
  interface Group {
    propertyId: number
    propertyName: string
    multiUnit: boolean
    rows: TimelineRow[]
    minUrgency: number
  }

  const groups: Group[] = []

  for (const p of props.properties) {
    const group: Group = {
      propertyId: p.id,
      propertyName: p.name,
      multiUnit: p.units.length >= 2,
      rows: [],
      minUrgency: Infinity,
    }

    if (p.units.length === 0) {
      // Unitless property — use property-level lease info
      const info = p.property_active_lease_info
      const days = info?.end_date ? daysBetween(info.end_date) : null
      const b = badge(days)
      group.rows.push({
        key: `p-${p.id}`,
        isHeader: false,
        indented: false,
        propertyId: p.id,
        propertyName: p.name,
        label: p.name,
        tenantName: info?.tenant_name ?? null,
        endDateFormatted: info?.end_date ? formatDate(info.end_date) : null,
        daysRemaining: days,
        badgeClass: b.cls,
        badgeText: b.text,
        actionTo: '/leases/build',
        actionLabel: info ? 'Renew' : 'Create lease',
        actionIcon: info ? RefreshCw : FilePlus2,
      })
      group.minUrgency = urgency(days)
    } else {
      for (const u of p.units) {
        const info = u.active_lease_info
        const days = info?.end_date ? daysBetween(info.end_date) : null
        const b = badge(days)
        const urg = urgency(days)
        if (urg < group.minUrgency) group.minUrgency = urg

        group.rows.push({
          key: `u-${u.id}`,
          isHeader: false,
          indented: p.units.length >= 2,
          propertyId: p.id,
          propertyName: p.name,
          label: p.units.length >= 2 ? `Unit ${u.unit_number}` : p.name,
          tenantName: info?.tenant_name ?? null,
          endDateFormatted: info?.end_date ? formatDate(info.end_date) : null,
          daysRemaining: days,
          badgeClass: b.cls,
          badgeText: b.text,
          actionTo: '/leases/build',
          actionLabel: info ? 'Renew' : 'Create lease',
          actionIcon: info ? RefreshCw : FilePlus2,
        })
      }

      // Sort units within group by urgency
      group.rows.sort((a, b) => urgency(a.daysRemaining) - urgency(b.daysRemaining))
    }

    groups.push(group)
  }

  // Sort groups by most urgent unit
  groups.sort((a, b) => a.minUrgency - b.minUrgency)

  // Flatten with headers
  const flat: TimelineRow[] = []
  for (const g of groups) {
    if (g.multiUnit) {
      flat.push({
        key: `hdr-${g.propertyId}`,
        isHeader: true,
        indented: false,
        propertyId: g.propertyId,
        propertyName: g.propertyName,
        label: g.propertyName,
        tenantName: null,
        endDateFormatted: null,
        daysRemaining: null,
        badgeClass: '',
        badgeText: '',
        actionTo: '',
        actionLabel: '',
        actionIcon: Building2,
      })
    }
    flat.push(...g.rows)
  }

  return flat
})

// Cap display rows to MAX_UNIT_ROWS (excluding headers)
const displayRows = computed(() => {
  let unitCount = 0
  const result: TimelineRow[] = []
  for (const row of timelineRows.value) {
    if (row.isHeader) {
      // Only include header if the next unit row will be within limit
      result.push(row)
      continue
    }
    if (unitCount >= MAX_UNIT_ROWS) break
    unitCount++
    result.push(row)
  }
  // Remove trailing headers that have no unit rows after them
  while (result.length > 0 && result[result.length - 1].isHeader) {
    result.pop()
  }
  return result
})

const overflowCount = computed(() => {
  const totalUnits = timelineRows.value.filter(r => !r.isHeader).length
  const shownUnits = displayRows.value.filter(r => !r.isHeader).length
  return Math.max(0, totalUnits - shownUnits)
})
</script>

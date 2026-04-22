<template>
  <div class="space-y-10 max-w-3xl mx-auto pb-16">
    <PageHeader
      title="Component Library"
      subtitle="A live preview of shared state components used across the admin SPA."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Component Library' }]"
    />

    <!-- LoadingState variants -->
    <section class="space-y-4">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">LoadingState</h2>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Table variant (5 rows, with avatar + badge)</div>
        <LoadingState variant="table" :rows="5" show-avatar show-badge double-row />
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Cards variant (3 cards)</div>
        <div class="p-4">
          <LoadingState variant="cards" :rows="3" grid-cols="grid-cols-1 md:grid-cols-3" />
        </div>
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Detail variant</div>
        <div class="p-4">
          <LoadingState variant="detail" />
        </div>
      </div>
    </section>

    <!-- EmptyState variants -->
    <section class="space-y-4">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">EmptyState</h2>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">No properties (with primary CTA)</div>
        <EmptyState
          title="No properties yet"
          description="Add your first property to start managing your portfolio. It takes less than a minute."
          :icon="Building2"
        >
          <button class="btn-primary btn-sm">
            <Plus :size="14" /> Add Property
          </button>
          <template #secondary>
            <a href="#" class="text-xs text-gray-400 hover:text-navy underline underline-offset-2">Import from municipal bill</a>
          </template>
        </EmptyState>
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">No tenants (with router-link CTA)</div>
        <EmptyState
          title="No tenants yet"
          description="Tenants are registered automatically when you create a lease. Build your first lease to get started."
          :icon="Users"
        >
          <RouterLink to="/leases/build" class="btn-primary btn-sm">
            <FilePlus :size="14" /> Create Lease
          </RouterLink>
        </EmptyState>
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Filter match — no results</div>
        <EmptyState
          title="No matches"
          description="Try adjusting your filters or search term."
          :icon="SearchX"
        >
          <button class="btn-secondary btn-sm">Clear filters</button>
        </EmptyState>
      </div>
    </section>

    <!-- ErrorState variants -->
    <section class="space-y-4">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">ErrorState</h2>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Generic error with retry</div>
        <ErrorState :on-retry="simulateRetry" />
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Offline / network error</div>
        <ErrorState
          title="You're offline"
          message="Check your internet connection and try again."
          :offline="true"
          :on-retry="simulateRetry"
        />
      </div>

      <div class="card overflow-hidden">
        <div class="px-5 py-3 border-b border-gray-100 text-xs font-medium text-gray-500">Error without retry (read-only context)</div>
        <ErrorState
          title="Could not load lease"
          message="This lease may have been deleted or you may not have access."
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Building2, FilePlus, Plus, SearchX, Users } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import EmptyState from '../../components/states/EmptyState.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'

async function simulateRetry() {
  await new Promise((resolve) => setTimeout(resolve, 800))
}
</script>

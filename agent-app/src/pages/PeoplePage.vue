<template>
  <q-page class="people-page">

    <!-- ── Search + segment ── -->
    <div class="people-head">
      <q-input
        v-model="search"
        dense
        outlined
        :rounded="isIos"
        placeholder="Search people"
        class="people-search"
      >
        <template v-slot:prepend>
          <q-icon name="search" color="grey-6" />
        </template>
      </q-input>

      <div class="segment">
        <button
          v-for="s in segments"
          :key="s.id"
          class="segment-item"
          :class="{ 'segment-item--active': activeSegment === s.id }"
          @click="activeSegment = s.id"
        >
          {{ s.label }}
          <span class="segment-count">{{ s.count }}</span>
        </button>
      </div>
    </div>

    <!-- ── Fresh matches banner ── -->
    <div v-if="activeSegment === 'prospects' && matches.length > 0" class="match-banner">
      <q-icon name="auto_awesome" size="18px" color="secondary" />
      <div class="match-banner-body">
        <div class="match-banner-title">{{ matches.length }} fresh matches ready</div>
        <div class="match-banner-sub">AI matched your prospects to new listings</div>
      </div>
      <q-btn
        unelevated
        :rounded="isIos"
        color="secondary"
        size="sm"
        label="Send all"
        class="match-banner-cta"
      />
    </div>

    <!-- ── List body ── -->
    <q-pull-to-refresh @refresh="loadData">

      <template v-if="activeSegment === 'prospects'">
        <div class="section-label">Ranked by match fit</div>
        <q-card flat class="list-card">
          <q-list separator>
            <q-item
              v-for="p in filteredProspects"
              :key="p.id"
              clickable
              v-ripple
            >
              <q-item-section avatar>
                <q-avatar :size="AVATAR_LIST" :style="{ background: p.avatarBg, color: 'white' }">
                  {{ p.initials }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ p.name }}</q-item-label>
                <q-item-label caption class="prospect-meta">
                  <span>{{ p.area }}</span>
                  <span class="dot">·</span>
                  <span>{{ p.budget }}</span>
                  <span class="dot">·</span>
                  <span>{{ p.bedrooms }}</span>
                </q-item-label>
                <q-item-label caption v-if="p.matchListing" class="match-line">
                  <q-icon name="arrow_forward" size="11px" />
                  {{ p.matchListing }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="score-pill" :class="`score-pill--${p.tier}`">{{ p.score }}</div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </template>

      <template v-else-if="activeSegment === 'landlords'">
        <q-card flat class="list-card">
          <q-list separator>
            <q-item v-for="l in landlords" :key="l.id" clickable v-ripple>
              <q-item-section avatar>
                <q-avatar :size="AVATAR_LIST" color="primary" text-color="white">{{ l.initials }}</q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ l.name }}</q-item-label>
                <q-item-label caption>{{ l.properties }} · {{ l.mandateStatus }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-5" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </template>

      <template v-else-if="activeSegment === 'tenants'">
        <q-card flat class="list-card">
          <q-list separator>
            <q-item v-for="t in tenants" :key="t.id" clickable v-ripple>
              <q-item-section avatar>
                <q-avatar :size="AVATAR_LIST" color="positive" text-color="white">{{ t.initials }}</q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">{{ t.name }}</q-item-label>
                <q-item-label caption>{{ t.property }} · Renewal {{ t.renewalIn }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-badge :color="t.healthColor" :label="`${t.health}%`" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </template>

      <div class="tab-bar-spacer" />
    </q-pull-to-refresh>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { usePlatform } from '../composables/usePlatform'
import { AVATAR_LIST } from '../utils/designTokens'

const { isIos } = usePlatform()
const setPageTitle = inject<(t: string | null) => void>('setPageTitle')

type SegmentId = 'prospects' | 'landlords' | 'tenants'
const activeSegment = ref<SegmentId>('prospects')
const search = ref('')

// Stubbed data — future: wire to backend /people endpoints
const prospects = ref([
  { id: 1,  name: 'John Dlamini',       initials: 'JD', area: 'Stellenbosch Central', budget: 'R 15–18k', bedrooms: '2 bed', score: 94, tier: 'top',    matchListing: '14 Bosch St',    avatarBg: '#2B2D6E' },
  { id: 2,  name: 'Nomvula Zulu',       initials: 'NZ', area: 'Dalsig',               budget: 'R 12–14k', bedrooms: '1 bed', score: 88, tier: 'strong', matchListing: '22 De Klerk Ave', avatarBg: '#3c3f8f' },
  { id: 3,  name: 'Andrew Meyer',       initials: 'AM', area: 'Welgevonden',          budget: 'R 20–25k', bedrooms: '3 bed', score: 81, tier: 'strong', matchListing: '14 Bosch St',     avatarBg: '#4a4dab' },
  { id: 4,  name: 'Kholwa Ndlovu',      initials: 'KN', area: 'Techno Park',          budget: 'R 8–10k',  bedrooms: '1 bed', score: 72, tier: 'fair',   matchListing: '',                avatarBg: '#6366d4' },
  { id: 5,  name: 'Sarah van der Berg', initials: 'SB', area: 'Paradyskloof',         budget: 'R 30k+',   bedrooms: '4 bed', score: 68, tier: 'fair',   matchListing: '',                avatarBg: '#8287e6' },
  { id: 6,  name: 'Pieter Botha',       initials: 'PB', area: 'Die Boord',            budget: 'R 14–16k', bedrooms: '2 bed', score: 54, tier: 'weak',   matchListing: '',                avatarBg: '#9fa3ef' },
])

const matches = computed(() => prospects.value.filter((p) => p.matchListing))

const landlords = ref([
  { id: 1, name: 'M. Adams',       initials: 'MA', properties: '3 properties · R 82k/mo billed',   mandateStatus: 'Active' },
  { id: 2, name: 'G. Van Wyk',     initials: 'GV', properties: '1 property · R 22k/mo billed',    mandateStatus: 'Pitching' },
  { id: 3, name: 'AirCent Pty',    initials: 'AC', properties: '5 properties · R 140k/mo billed',  mandateStatus: 'Active' },
  { id: 4, name: 'F. Mthembu',     initials: 'FM', properties: '1 property · R 18k/mo billed',    mandateStatus: 'Active' },
])

const tenants = ref([
  { id: 1, name: 'Lisa Bosman',    initials: 'LB', property: '14 Bosch St',       renewalIn: '3 months',  health: 97, healthColor: 'positive' },
  { id: 2, name: 'D. Khumalo',     initials: 'DK', property: '22 De Klerk Ave',   renewalIn: '8 months',  health: 82, healthColor: 'positive' },
  { id: 3, name: 'T. Pieterse',    initials: 'TP', property: '7A Ryneveld',      renewalIn: '1 month',   health: 64, healthColor: 'warning'  },
])

const segments = computed(() => ([
  { id: 'prospects' as SegmentId, label: 'Prospects', count: prospects.value.length },
  { id: 'landlords' as SegmentId, label: 'Landlords', count: landlords.value.length },
  { id: 'tenants' as SegmentId,   label: 'Tenants',   count: tenants.value.length },
]))

const filteredProspects = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return prospects.value
  return prospects.value.filter((p) =>
    p.name.toLowerCase().includes(q) ||
    p.area.toLowerCase().includes(q) ||
    (p.matchListing ?? '').toLowerCase().includes(q),
  )
})

async function loadData(done?: () => void) {
  done?.()
}

onMounted(() => {
  setPageTitle?.('People')
})
</script>

<style scoped lang="scss">
.people-page {
  background: var(--klikk-surface);
  padding: 12px 0 0;
  min-height: 100vh;
}

.people-head {
  padding: 0 16px 12px;
}

.people-search {
  :deep(.q-field__control) {
    background: white;
  }
}

.segment {
  display: flex;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 3px;
  margin-top: 10px;
}

.segment-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: none;
  border: none;
  padding: 7px 0;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  border-radius: 6px;
  transition: all 0.15s;

  &--active {
    background: white;
    color: $primary;
    box-shadow: var(--klikk-shadow-soft);
  }

  &:active:not(&--active) {
    opacity: 0.7;
  }
}

.segment-count {
  font-size: 11px;
  font-weight: 700;
  color: inherit;
  opacity: 0.7;
}

/* ── Match banner ── */
.match-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 16px 14px;
  padding: 12px 14px;
  background: linear-gradient(135deg, rgba(255, 61, 127, 0.1) 0%, rgba(255, 61, 127, 0.02) 100%);
  border: 1px solid rgba(255, 61, 127, 0.2);
  border-radius: 12px;
}

.match-banner-body {
  flex: 1;
}

.match-banner-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--klikk-text-primary);
}

.match-banner-sub {
  font-size: 11px;
  color: var(--klikk-text-secondary);
  margin-top: 1px;
}

.match-banner-cta {
  font-weight: 600;
  font-size: 12px;
  padding: 4px 12px;
}

/* ── List body ── */
.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0 18px 8px;
}

.list-card {
  background: white;
  border: 1px solid var(--klikk-card-border);
  border-radius: var(--klikk-radius-card);
  box-shadow: var(--klikk-shadow-soft);
  margin: 0 16px 12px;
  overflow: hidden;
}

.prospect-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--klikk-text-secondary);
}

.dot {
  opacity: 0.5;
}

.match-line {
  display: flex;
  align-items: center;
  gap: 3px;
  color: $secondary;
  font-weight: 600;
  margin-top: 2px;
}

/* Score pill (same pattern as Pipeline) */
.score-pill {
  font-size: 12px;
  font-weight: 800;
  padding: 4px 9px;
  border-radius: 999px;
  letter-spacing: -0.01em;

  &--top    { background: rgba(20, 184, 166, 0.12); color: $positive; }
  &--strong { background: rgba(43, 45, 110, 0.12);  color: $primary;  }
  &--fair   { background: rgba(245, 158, 11, 0.12); color: $warning;  }
  &--weak   { background: rgba(220, 38, 38, 0.10);  color: $negative; }
}

.tab-bar-spacer {
  height: calc(90px + env(safe-area-inset-bottom, 0px));
}
</style>

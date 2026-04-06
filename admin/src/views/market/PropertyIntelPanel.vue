<template>
  <div class="flex flex-col h-full">
    <!-- Loading skeleton -->
    <div v-if="loading" class="p-5 space-y-4 animate-pulse flex-1">
      <div class="h-6 bg-gray-100 rounded w-2/3" />
      <div class="h-4 bg-gray-100 rounded" />
      <div class="h-4 bg-gray-100 rounded w-4/5" />
      <div class="h-32 bg-gray-100 rounded mt-4" />
    </div>

    <template v-else-if="listing">
      <!-- ── Property header ── -->
      <div class="px-5 py-4 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-start gap-2">
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-gray-900 text-sm leading-snug">
              {{ listing.title || listing.raw_address || 'Property' }}
            </div>
            <div class="text-xs text-gray-500 mt-0.5">
              {{ listing.suburb }}{{ listing.suburb && listing.area ? ' · ' : '' }}{{ listing.area?.replace(/_/g, ' ') }}
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <span
              class="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide"
              :class="listing.listing_type === 'rent' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'"
            >
              {{ listing.listing_type }}
            </span>
            <span v-if="listing.is_duplicate" class="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium">
              dup
            </span>
          </div>
        </div>

        <!-- AI badges row -->
        <div v-if="listing.ai_property_type" class="flex flex-wrap gap-1.5 mt-2.5">
          <span class="ai-badge bg-indigo-50 text-indigo-700">{{ listing.ai_property_type }}</span>
          <span v-if="listing.ai_condition" :class="aiConditionClass(listing.ai_condition)" class="ai-badge">{{ listing.ai_condition }}</span>
          <span v-if="listing.ai_style" class="ai-badge bg-purple-50 text-purple-700">{{ listing.ai_style }}</span>
          <span v-if="listing.ai_classification_confidence != null" class="ai-badge bg-gray-50 text-gray-500">
            {{ Math.round(listing.ai_classification_confidence * 100) }}% conf.
          </span>
        </div>
      </div>

      <!-- ── Tab bar ── -->
      <div class="border-b border-gray-100 px-5 flex-shrink-0">
        <nav class="flex gap-0 -mb-px">
          <button
            v-for="tab in TABS"
            :key="tab.id"
            class="px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap"
            :class="activeTab === tab.id
              ? 'border-navy text-navy'
              : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
            <span v-if="tab.id === 'photos' && listing.photos?.length" class="ml-1 text-gray-400">({{ listing.photos.length }})</span>
            <span v-if="tab.id === 'nearby' && listing.nearby_places?.length" class="ml-1 text-gray-400">({{ listing.nearby_places.length }})</span>
          </button>
        </nav>
      </div>

      <!-- ── Tab content (scrollable) ── -->
      <div class="flex-1 overflow-y-auto">

        <!-- Overview -->
        <div v-if="activeTab === 'overview'" class="p-5 space-y-5">

          <!-- Price -->
          <div>
            <div class="text-2xl font-bold text-gray-900">{{ activePrice }}</div>
            <div v-if="listing.previous_price" class="text-xs text-gray-400 mt-0.5">
              Previously {{ fmtPrice(listing.previous_price) }}
              <span v-if="listing.price_changed_at"> · changed {{ relDate(listing.price_changed_at) }}</span>
            </div>
          </div>

          <div class="border-t border-gray-100" />

          <!-- Features -->
          <div>
            <div class="section-label">Features</div>
            <div class="grid grid-cols-3 gap-x-4 gap-y-3">
              <div v-if="listing.bedrooms != null">
                <div class="label">Beds</div>
                <div class="detail-value">{{ listing.bedrooms }}</div>
              </div>
              <div v-if="listing.bathrooms != null">
                <div class="label">Baths</div>
                <div class="detail-value">{{ listing.bathrooms }}</div>
              </div>
              <div v-if="listing.parking != null">
                <div class="label">Parking</div>
                <div class="detail-value">{{ listing.parking }}</div>
              </div>
              <div v-if="listing.floor_size_m2">
                <div class="label">Floor</div>
                <div class="detail-value">{{ listing.floor_size_m2 }} m²</div>
              </div>
              <div v-if="listing.erf_size_m2">
                <div class="label">Erf</div>
                <div class="detail-value">{{ listing.erf_size_m2 }} m²</div>
              </div>
              <div v-if="listing.property_type">
                <div class="label">Type</div>
                <div class="detail-value capitalize">{{ listing.property_type }}</div>
              </div>
              <div v-if="listing.is_furnished != null">
                <div class="label">Furnished</div>
                <div class="detail-value">{{ listing.is_furnished ? 'Yes' : 'No' }}</div>
              </div>
              <div v-if="listing.pets_allowed != null">
                <div class="label">Pets</div>
                <div class="detail-value">{{ listing.pets_allowed ? 'Yes' : 'No' }}</div>
              </div>
            </div>
          </div>

          <div class="border-t border-gray-100" />

          <!-- AI classification confidence bar -->
          <div v-if="listing.ai_classification_confidence != null">
            <div class="section-label">AI Confidence</div>
            <div class="flex items-center gap-2">
              <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="listing.ai_classification_confidence >= 0.75 ? 'bg-emerald-500' : listing.ai_classification_confidence >= 0.5 ? 'bg-amber-400' : 'bg-red-400'"
                  :style="`width:${Math.round(listing.ai_classification_confidence * 100)}%`"
                />
              </div>
              <span class="text-xs text-gray-500 w-8 text-right">{{ Math.round(listing.ai_classification_confidence * 100) }}%</span>
            </div>
          </div>

          <div class="border-t border-gray-100" />

          <!-- Location -->
          <div>
            <div class="section-label">Location</div>
            <div class="space-y-2">
              <div>
                <div class="label">Address</div>
                <div class="detail-value">{{ listing.raw_address || listing.suburb || '—' }}</div>
              </div>
              <div v-if="listing.latitude" class="flex items-center justify-between">
                <div>
                  <div class="label">Coordinates</div>
                  <div class="detail-value font-mono text-xs">{{ listing.latitude?.toFixed(5) }}, {{ listing.longitude?.toFixed(5) }}</div>
                </div>
                <a
                  :href="`https://maps.google.com/?q=${listing.latitude},${listing.longitude}`"
                  target="_blank"
                  class="text-xs text-navy hover:underline flex items-center gap-1 flex-shrink-0"
                >
                  <MapPin :size="11" /> Maps
                </a>
              </div>
            </div>
          </div>

          <!-- Agency -->
          <div v-if="listing.agency">
            <div class="border-t border-gray-100 mb-5" />
            <div class="section-label">Agency</div>
            <div class="flex items-center gap-3">
              <img
                v-if="listing.agency.agency_logo_file || listing.agency.photo_file"
                :src="listing.agency.agency_logo_file || listing.agency.photo_file"
                class="w-9 h-9 rounded-lg object-contain border border-gray-100 bg-white p-0.5 flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">{{ listing.agency.name || listing.agency.agency_name }}</div>
                <div v-if="listing.agency.phone" class="text-xs text-gray-500">{{ listing.agency.phone }}</div>
              </div>
            </div>
          </div>

          <!-- Source -->
          <div class="border-t border-gray-100" />
          <div class="flex items-center justify-between">
            <span class="text-xs text-gray-500">{{ sourceLabel(listing.source) }}</span>
            <a :href="listing.source_url" target="_blank" class="btn-ghost btn-sm flex items-center gap-1.5 text-xs">
              <ExternalLink :size="12" /> View listing
            </a>
          </div>

          <!-- Description -->
          <div v-if="listing.description">
            <div class="border-t border-gray-100 mb-5" />
            <div class="section-label">Description</div>
            <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ listing.description }}</p>
          </div>
        </div>

        <!-- Photos -->
        <div v-else-if="activeTab === 'photos'" class="p-4">
          <div v-if="listing.photos?.length" class="grid grid-cols-2 gap-2">
            <div
              v-for="photo in listing.photos"
              :key="photo.id"
              class="aspect-video bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-navy/30 transition"
              @click="lightboxSrc = photo.photo_file || photo.source_url; lightboxOpen = true"
            >
              <img
                :src="photo.photo_file || photo.source_url"
                :alt="`Photo ${photo.position + 1}`"
                class="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
          </div>
          <div v-else class="text-sm text-gray-400 py-10 text-center">No photos downloaded yet.</div>
        </div>

        <!-- Street View -->
        <div v-else-if="activeTab === 'streetview'" class="p-5 space-y-4">
          <div v-if="listing.street_view?.api_status === 'OK'">
            <div class="rounded-xl overflow-hidden border border-gray-100">
              <img :src="listing.street_view.photo_file" alt="Street View" class="w-full object-cover" />
            </div>
            <div class="mt-2 flex items-center justify-between text-xs text-gray-400">
              <span>Fetched {{ relDate(listing.street_view.fetched_at) }}</span>
              <a
                v-if="listing.latitude"
                :href="`https://maps.google.com/?cbll=${listing.latitude},${listing.longitude}&layer=c`"
                target="_blank"
                class="text-navy hover:underline flex items-center gap-1"
              >
                <ExternalLink :size="11" /> Street View
              </a>
            </div>
          </div>
          <div v-else-if="listing.street_view?.api_status === 'ZERO_RESULTS'" class="text-sm text-gray-400 py-10 text-center">
            No street view at this location.
          </div>
          <div v-else class="text-sm text-gray-400 py-10 text-center">
            Not fetched — run <code class="bg-gray-100 px-1 rounded text-xs">enrich_listings</code>
          </div>
          <div v-if="listing.latitude" class="pt-2">
            <div class="section-label">Satellite</div>
            <a
              :href="`https://maps.google.com/?q=${listing.latitude},${listing.longitude}&t=k`"
              target="_blank"
              class="text-xs text-navy hover:underline flex items-center gap-1"
            >
              <MapPin :size="11" /> Open satellite view
            </a>
          </div>
        </div>

        <!-- Nearby -->
        <div v-else-if="activeTab === 'nearby'" class="p-5">
          <div v-if="listing.nearby_places?.length">
            <div v-for="(places, category) in groupedPlaces" :key="category" class="mb-5">
              <div class="section-label capitalize">{{ String(category).replace(/_/g, ' ') }}</div>
              <div class="space-y-2">
                <div
                  v-for="p in places"
                  :key="p.id"
                  class="flex items-center gap-3 py-1.5 border-b border-gray-50 last:border-0"
                >
                  <div class="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <component :is="categoryIcon(p.category)" :size="13" class="text-gray-500" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm text-gray-900 truncate">{{ p.name }}</div>
                    <div class="text-xs text-gray-400 flex gap-2">
                      <span>{{ fmtDist(p.distance_m) }}</span>
                      <span v-if="p.walk_minutes">· {{ p.walk_minutes }}min walk</span>
                      <span v-else-if="p.drive_minutes">· {{ p.drive_minutes }}min drive</span>
                    </div>
                  </div>
                  <div v-if="p.rating" class="text-xs text-amber-500 font-medium">★ {{ p.rating }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-gray-400 py-10 text-center">
            No nearby places — run <code class="bg-gray-100 px-1 rounded text-xs">enrich_listings</code>
          </div>
        </div>

        <!-- History -->
        <div v-else-if="activeTab === 'history'" class="p-5 space-y-5">
          <div class="section-label">Timeline</div>
          <ol class="relative border-l border-gray-200 ml-3 space-y-5">
            <li v-for="ev in timelineEvents" :key="ev.label" class="ml-5">
              <div class="absolute -left-[9px] w-4 h-4 rounded-full flex items-center justify-center" :class="ev.color">
                <component :is="ev.icon" :size="9" class="text-white" />
              </div>
              <div class="text-xs font-medium text-gray-900">{{ ev.label }}</div>
              <div class="text-xs text-gray-400">{{ fmtFull(ev.date) }}</div>
              <div v-if="ev.detail" class="text-xs text-gray-500 mt-0.5">{{ ev.detail }}</div>
            </li>
          </ol>

          <div class="border-t border-gray-100 pt-4">
            <div class="section-label">Metadata</div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <div class="label">Source ID</div>
                <div class="detail-value font-mono text-xs break-all">{{ listing.source_listing_id || '—' }}</div>
              </div>
              <div>
                <div class="label">Listed</div>
                <div class="detail-value text-xs">{{ fmtFull(listing.listed_at) }}</div>
              </div>
              <div v-if="listing.enriched_at">
                <div class="label">Enriched</div>
                <div class="detail-value text-xs">{{ fmtFull(listing.enriched_at) }}</div>
              </div>
              <div v-if="listing.ai_classified_at">
                <div class="label">Classified</div>
                <div class="detail-value text-xs">{{ fmtFull(listing.ai_classified_at) }}</div>
              </div>
              <div v-if="listing.duplicate_score != null">
                <div class="label">Dup. score</div>
                <div class="detail-value">{{ listing.duplicate_score }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div v-else class="flex-1 flex flex-col items-center justify-center text-center p-8 text-gray-400">
      <TrendingUp :size="36" class="mb-3 opacity-30" />
      <div class="text-sm font-medium">Select a listing</div>
      <div class="text-xs mt-1">Click any row to view property intelligence</div>
    </div>
  </div>

  <!-- Lightbox -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="lightboxOpen"
        class="fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4"
        @click="lightboxOpen = false"
      >
        <img :src="lightboxSrc" class="max-w-full max-h-full rounded-lg object-contain" @click.stop />
        <button class="absolute top-4 right-4 text-white/70 hover:text-white" @click="lightboxOpen = false">
          <X :size="24" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import api from '../../api'
import {
  MapPin, ExternalLink, X, TrendingUp,
  UtensilsCrossed, ShoppingCart, GraduationCap, Dumbbell,
  HeartPulse, Trees, Banknote, Bus, Star,
  Eye, Sparkles, RefreshCw, Calendar,
} from 'lucide-vue-next'

const props = defineProps<{ listingId: number | null }>()

const TABS = [
  { id: 'overview',   label: 'Overview' },
  { id: 'photos',     label: 'Photos' },
  { id: 'streetview', label: 'Street View' },
  { id: 'nearby',     label: 'Nearby' },
  { id: 'history',    label: 'History' },
]

const activeTab   = ref('overview')
const loading     = ref(false)
const listing     = ref<any>(null)
const lightboxOpen = ref(false)
const lightboxSrc  = ref('')

watch(() => props.listingId, async (id) => {
  if (!id) { listing.value = null; return }
  activeTab.value = 'overview'
  loading.value = true
  try {
    const { data } = await api.get(`/market-data/listings/${id}/`)
    listing.value = data
  } finally {
    loading.value = false
  }
}, { immediate: true })

// ── Computed ──

const activePrice = computed(() => {
  const l = listing.value
  if (!l) return '—'
  const price = l.rental_price || l.asking_price
  if (!price) return '—'
  const val = Number(price).toLocaleString('en-ZA', { maximumFractionDigits: 0 })
  return l.listing_type === 'rent' ? `R${val} / month` : `R${val}`
})

const groupedPlaces = computed(() => {
  if (!listing.value?.nearby_places?.length) return {}
  const groups: Record<string, any[]> = {}
  for (const p of listing.value.nearby_places) {
    const cat = p.category || 'other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(p)
  }
  for (const cat of Object.keys(groups)) {
    groups[cat].sort((a: any, b: any) => (a.distance_m ?? 9999) - (b.distance_m ?? 9999))
  }
  return groups
})

const timelineEvents = computed(() => {
  const l = listing.value
  if (!l) return []
  const evs: any[] = []
  if (l.first_seen_at) evs.push({ label: 'First scraped', date: l.first_seen_at, icon: Eye, color: 'bg-navy', detail: `via ${sourceLabel(l.source)}` })
  if (l.listed_at && l.listed_at !== l.first_seen_at) evs.push({ label: 'Listed', date: l.listed_at, icon: Calendar, color: 'bg-blue-500' })
  if (l.price_changed_at) evs.push({ label: 'Price changed', date: l.price_changed_at, icon: Banknote, color: 'bg-amber-500', detail: `Previous: ${fmtPrice(l.previous_price)}` })
  if (l.enriched_at) evs.push({ label: 'Enriched', date: l.enriched_at, icon: MapPin, color: 'bg-emerald-500' })
  if (l.ai_classified_at) evs.push({ label: 'AI classified', date: l.ai_classified_at, icon: Sparkles, color: 'bg-purple-500', detail: `${l.ai_property_type} / ${l.ai_condition} / ${l.ai_style}` })
  if (l.last_seen_at) evs.push({ label: 'Last seen', date: l.last_seen_at, icon: RefreshCw, color: 'bg-gray-400' })
  return evs.filter(e => e.date).sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime())
})

// ── Helpers ──

function sourceLabel(s: string) {
  return s?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) ?? s
}
function fmtPrice(p: any) {
  if (!p) return '—'
  return `R${Number(p).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
}
function fmtDist(m: number | null) {
  if (m == null) return ''
  return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`
}
function relDate(iso: string | null) {
  if (!iso) return '—'
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}
function fmtFull(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-ZA', { dateStyle: 'medium', timeStyle: 'short' })
}
function aiConditionClass(c: string) {
  if (c === 'well-maintained') return 'bg-emerald-50 text-emerald-700'
  if (c === 'average') return 'bg-amber-50 text-amber-700'
  if (c === 'poor') return 'bg-red-50 text-red-700'
  return 'bg-gray-50 text-gray-500'
}
function categoryIcon(cat: string) {
  const map: Record<string, any> = {
    restaurant: UtensilsCrossed, cafe: UtensilsCrossed,
    supermarket: ShoppingCart,   grocery: ShoppingCart,
    school: GraduationCap,       gym: Dumbbell,
    hospital: HeartPulse,        pharmacy: HeartPulse,
    park: Trees,                 bus_station: Bus,
    bank: Banknote,
  }
  return map[cat] || Star
}
</script>

<style scoped>
.section-label { @apply text-xs font-semibold uppercase tracking-wide text-navy mb-2; }
.label         { @apply text-[11px] font-medium text-gray-400 uppercase tracking-wide mb-0.5; }
.detail-value  { @apply text-sm text-gray-900; }
.ai-badge      { @apply text-xs font-medium px-2 py-0.5 rounded-full; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

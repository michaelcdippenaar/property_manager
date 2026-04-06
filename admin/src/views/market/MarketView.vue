<template>
  <!-- Full-height split-pane: break out of AppLayout p-6 padding -->
  <div class="-m-6 flex h-[calc(100vh-3.5rem)] overflow-hidden">

    <!-- ── Left: listings list ── -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden border-r border-gray-200">

      <!-- Filter bar -->
      <div class="flex-shrink-0 flex flex-wrap items-center gap-2.5 px-4 py-3 border-b border-gray-100 bg-white">
        <SearchInput v-model="search" placeholder="Search suburb, title…" class="w-48 flex-shrink-0" />

        <select v-model="filterArea" class="input text-sm py-1.5 w-36 flex-shrink-0">
          <option value="">All areas</option>
          <option v-for="a in AREAS" :key="a.value" :value="a.value">{{ a.label }}</option>
        </select>

        <select v-model="filterType" class="input text-sm py-1.5 w-28 flex-shrink-0">
          <option value="">Rent &amp; Sale</option>
          <option value="rent">Rent</option>
          <option value="sale">Sale</option>
        </select>

        <select v-model="filterBeds" class="input text-sm py-1.5 w-24 flex-shrink-0">
          <option value="">Any beds</option>
          <option v-for="n in [1,2,3,4,5]" :key="n" :value="String(n)">{{ n }}bd</option>
        </select>

        <span class="ml-auto text-xs text-gray-400 flex-shrink-0">{{ total }} listings</span>

        <button class="flex-shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" @click="loadListings">
          <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>

      <!-- Table -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="loading" class="p-6 space-y-3 animate-pulse">
          <div v-for="i in 10" :key="i" class="h-5 bg-gray-100 rounded" />
        </div>

        <table v-else-if="listings.length" class="table-wrap">
          <thead class="sticky top-0 bg-white z-10">
            <tr>
              <th>Property</th>
              <th>Beds</th>
              <th class="text-right">Price</th>
              <th>AI</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="l in listings"
              :key="l.id"
              class="cursor-pointer hover:bg-gray-50 transition-colors"
              :class="selectedId === l.id ? 'bg-indigo-50 hover:bg-indigo-50' : ''"
              @click="selectedId = l.id"
            >
              <td class="max-w-[200px]">
                <div class="font-medium text-gray-900 truncate text-xs">{{ l.title || l.raw_address || '—' }}</div>
                <div class="text-[11px] text-gray-400 truncate">{{ l.suburb || l.area?.replace(/_/g, ' ') }}</div>
              </td>
              <td class="text-gray-600 text-sm">{{ l.bedrooms ?? '—' }}</td>
              <td class="text-right text-sm font-medium text-gray-900 whitespace-nowrap">{{ formatPrice(l) }}</td>
              <td>
                <div class="flex flex-col gap-0.5">
                  <span v-if="l.ai_property_type" class="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-medium w-fit">{{ l.ai_property_type }}</span>
                  <span v-if="l.ai_condition" :class="conditionClass(l.ai_condition)" class="text-[10px] px-1.5 py-0.5 rounded-full font-medium w-fit">{{ l.ai_condition }}</span>
                </div>
              </td>
              <td>
                <span class="text-[11px] text-gray-500">{{ sourceShort(l.source) }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <EmptyState
          v-else
          title="No listings found"
          description="Run scrape_winelands to fetch market data from portals."
          :icon="BarChart2"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex-shrink-0 px-4 py-2.5 border-t border-gray-100 bg-white flex items-center justify-between">
        <span class="text-xs text-gray-500">Page {{ page }} / {{ totalPages }}</span>
        <div class="flex gap-1.5">
          <button class="btn-ghost btn-sm" :disabled="page <= 1" @click="page--; loadListings()">Prev</button>
          <button class="btn-ghost btn-sm" :disabled="page >= totalPages" @click="page++; loadListings()">Next</button>
        </div>
      </div>
    </div>

    <!-- ── Right: property intel panel ── -->
    <div class="w-[440px] flex-shrink-0 bg-white overflow-hidden">
      <PropertyIntelPanel :listing-id="selectedId" />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import api from '../../api'
import SearchInput from '../../components/SearchInput.vue'
import EmptyState from '../../components/EmptyState.vue'
import PropertyIntelPanel from './PropertyIntelPanel.vue'
import { RefreshCw, BarChart2 } from 'lucide-vue-next'

const AREAS = [
  { value: 'stellenbosch',       label: 'Stellenbosch' },
  { value: 'paarl',              label: 'Paarl' },
  { value: 'franschhoek',        label: 'Franschhoek' },
  { value: 'somerset_west',      label: 'Somerset West' },
  { value: 'strand',             label: 'Strand' },
  { value: 'city_bowl',          label: 'City Bowl' },
  { value: 'atlantic_seaboard',  label: 'Atlantic Seaboard' },
  { value: 'southern_suburbs',   label: 'Southern Suburbs' },
  { value: 'northern_suburbs_cpt', label: 'Northern Suburbs' },
  { value: 'helderberg',         label: 'Helderberg' },
  { value: 'false_bay',          label: 'False Bay' },
  { value: 'hout_bay',           label: 'Hout Bay' },
]

const loading    = ref(true)
const listings   = ref<any[]>([])
const total      = ref(0)
const page       = ref(1)
const PAGE_SIZE  = 20
const totalPages = ref(1)

const search     = ref('')
const filterArea = ref('')
const filterType = ref('')
const filterBeds = ref('')

const selectedId = ref<number | null>(null)

watch([search, filterArea, filterType, filterBeds], () => {
  page.value = 1
  loadListings()
})

onMounted(() => loadListings())

async function loadListings() {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page: page.value, page_size: PAGE_SIZE }
    if (search.value)     params.search       = search.value
    if (filterArea.value) params.area         = filterArea.value
    if (filterType.value) params.listing_type = filterType.value
    if (filterBeds.value) params.bedrooms     = filterBeds.value
    const { data } = await api.get('/market-data/listings/', { params })
    listings.value  = data.results ?? data
    total.value     = data.count ?? listings.value.length
    totalPages.value = Math.ceil(total.value / PAGE_SIZE)
  } finally {
    loading.value = false
  }
}

function formatPrice(l: any): string {
  const price = l.rental_price || l.asking_price
  if (!price) return '—'
  const val = Number(price).toLocaleString('en-ZA', { maximumFractionDigits: 0 })
  return l.listing_type === 'rent' ? `R${val}/mo` : `R${val}`
}

function conditionClass(c: string): string {
  if (c === 'well-maintained') return 'bg-emerald-50 text-emerald-700'
  if (c === 'average')         return 'bg-amber-50 text-amber-700'
  if (c === 'poor')            return 'bg-red-50 text-red-700'
  return 'bg-gray-50 text-gray-500'
}

function sourceShort(s: string): string {
  const map: Record<string, string> = {
    property24: 'P24', private_property: 'PP', gumtree: 'GT',
    iol_property: 'IOL', pam_golding: 'PG', seeff: 'Seeff',
    rentfind: 'RF', facebook: 'FB',
  }
  return map[s] ?? s
}
</script>

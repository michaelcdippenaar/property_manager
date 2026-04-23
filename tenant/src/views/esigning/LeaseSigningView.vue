<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="Lease & Signing" show-back back-label="Home" />

    <!-- Signed confirmation banner -->
    <Transition name="banner-slide">
      <div
        v-if="showSignedBanner"
        class="mx-4 mt-3 flex items-start gap-3 rounded-2xl bg-success-50 border border-success-200 px-4 py-3"
      >
        <div class="w-7 h-7 flex-shrink-0 rounded-full bg-success-100 flex items-center justify-center mt-0.5">
          <Check :size="14" class="text-success-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-success-800">Lease signed</p>
          <p class="text-xs text-success-700 mt-0.5">Awaiting countersignature from your agent</p>
        </div>
        <button @click="showSignedBanner = false" class="text-success-400 flex-shrink-0 mt-0.5 touchable">
          <X :size="16" />
        </button>
      </div>
    </Transition>

    <div class="scroll-page px-4 pt-4 pb-8 space-y-4">
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 2" :key="i" class="h-28 bg-white rounded-2xl animate-pulse" />
      </div>

      <div v-else-if="!lease" class="flex flex-col items-center justify-center pt-20 text-center">
        <div class="w-16 h-16 bg-navy/5 rounded-2xl flex items-center justify-center mb-4">
          <FileText :size="28" class="text-navy/30" />
        </div>
        <p class="font-semibold text-gray-700">No active lease found</p>
      </div>

      <template v-else>
        <!-- Lease card -->
        <div class="list-section">
          <div class="px-5 py-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-sm font-semibold text-gray-900">{{ lease.unit_label ?? lease.property_name }}</p>
                <p class="text-xs text-gray-500 mt-0.5">{{ lease.start_date }} – {{ lease.end_date }}</p>
              </div>
              <StatusBadge :value="lease.status" />
            </div>
          </div>
        </div>

        <!-- Signing submissions -->
        <div v-if="submissions.length > 0">
          <p class="label-upper px-1 mb-2">Signing Status</p>
          <div v-for="sub in submissions" :key="sub.id" class="list-section mb-3">
            <div class="px-5 py-4 space-y-3">
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold text-gray-900">{{ sub.template_name ?? 'Lease Agreement' }}</p>
                <StatusBadge :value="sub.status" />
              </div>

              <!-- Signers -->
              <div class="space-y-2">
                <div
                  v-for="signer in sub.signers"
                  :key="signer.id"
                  class="flex items-center gap-3"
                >
                  <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                    :class="signer.status === 'completed' ? 'bg-success-100' : signer.status === 'declined' ? 'bg-danger-100' : 'bg-gray-100'">
                    <Check v-if="signer.status === 'completed'" :size="14" class="text-success-600" />
                    <X v-else-if="signer.status === 'declined'" :size="14" class="text-danger-600" />
                    <Clock v-else :size="14" class="text-gray-400" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-700 truncate">{{ signer.name ?? signer.email }}</p>
                    <p class="text-xs text-gray-400 capitalize">{{ signer.role?.replace('_', ' ') }}</p>
                  </div>
                  <StatusBadge :value="signer.status" />
                </div>
              </div>

              <!-- Sign button (if my turn) — disabled while watching for completion -->
              <button
                v-if="myPendingSigner(sub)"
                class="w-full py-3 bg-accent text-white rounded-xl font-semibold text-sm ripple touchable disabled:opacity-60 disabled:cursor-not-allowed"
                :disabled="watchingSubId === sub.id"
                @click="openSigning(sub)"
              >
                <span v-if="watchingSubId === sub.id" class="inline-flex items-center gap-2">
                  <span class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin inline-block" />
                  Waiting for signing…
                </span>
                <span v-else>Sign Now</span>
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, X, Clock, FileText } from 'lucide-vue-next'
import { Capacitor } from '@capacitor/core'
import AppHeader from '../../components/AppHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useSigningStatus } from '../../composables/useSigningStatus'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const lease = ref<any>(null)
const submissions = ref<any[]>([])
const loading = ref(true)
const showSignedBanner = ref(false)
const watchingSubId = ref<number | null>(null)

const { signedAt, startSigningWatch, stopSigningWatch } = useSigningStatus()

function myPendingSigner(sub: any) {
  return sub.signers?.find((s: any) => s.email === auth.user?.email && s.status === 'pending')
}

async function refreshSubmissions() {
  if (!lease.value) return
  try {
    const subsRes = await api.get('/esigning/submissions/', { params: { lease: lease.value.id } })
    submissions.value = subsRes.data.results ?? subsRes.data
  } catch { /* non-fatal */ }
}

async function openSigning(sub: any) {
  const signer = myPendingSigner(sub)
  if (!signer?.signing_url) return

  // Build the signing URL, appending a returnUrl so the signing page can redirect back
  let url = signer.signing_url
  try {
    const parsed = new URL(url)
    // The return path is /signing on the tenant app (this very view)
    const returnPath = route.path || '/signing'
    parsed.searchParams.set('returnUrl', `${window.location.origin}${returnPath}`)
    url = parsed.toString()
  } catch { /* keep original URL on parse error */ }

  watchingSubId.value = sub.id

  if (Capacitor.isNativePlatform()) {
    const { Browser } = await import('@capacitor/browser')
    await startSigningWatch(lease.value.id, auth.user?.email ?? '')
    await Browser.open({ url })
  } else {
    // Open external tab
    window.open(url, '_blank')
    // Start watch: postMessage listener + polling
    await startSigningWatch(lease.value.id, auth.user?.email ?? '')
  }
}

// React to signing detection
watch(signedAt, async (val) => {
  if (!val) return
  watchingSubId.value = null
  await refreshSubmissions()
  showSignedBanner.value = true
})

// Handle `?signed=1` query param when redirected back by the signing page
onMounted(async () => {
  try {
    const leasesRes = await api.get('/leases/')
    const leases = leasesRes.data.results ?? leasesRes.data
    if (leases.length === 0) return
    lease.value = leases[0]

    const subsRes = await api.get('/esigning/submissions/', { params: { lease: lease.value.id } })
    submissions.value = subsRes.data.results ?? subsRes.data
  } finally {
    loading.value = false
  }

  // Show banner if redirected back from signing tab with ?signed=1, then strip the param
  if (route.query.signed === '1') {
    showSignedBanner.value = true
    router.replace({ query: { ...route.query, signed: undefined } })
  }
})

onUnmounted(() => {
  stopSigningWatch()
})
</script>

<style scoped>
.banner-slide-enter-active,
.banner-slide-leave-active {
  transition: all 0.3s ease;
}
.banner-slide-enter-from,
.banner-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

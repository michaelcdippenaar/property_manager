<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="Lease & Signing" show-back back-label="Home" />

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

              <!-- Sign button (if my turn) -->
              <button
                v-if="myPendingSigner(sub)"
                class="w-full py-3 bg-accent text-white rounded-xl font-semibold text-sm ripple touchable"
                @click="openSigning(sub)"
              >
                Sign Now
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Check, X, Clock, FileText } from 'lucide-vue-next'
import { Capacitor } from '@capacitor/core'
import AppHeader from '../../components/AppHeader.vue'
import StatusBadge from '../../components/StatusBadge.vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const lease = ref<any>(null)
const submissions = ref<any[]>([])
const loading = ref(true)

function myPendingSigner(sub: any) {
  return sub.signers?.find((s: any) => s.email === auth.user?.email && s.status === 'pending')
}

async function openSigning(sub: any) {
  const signer = myPendingSigner(sub)
  if (!signer?.signing_url) return
  const url = signer.signing_url

  if (Capacitor.isNativePlatform()) {
    const { Browser } = await import('@capacitor/browser')
    await Browser.open({ url })
  } else {
    window.open(url, '_blank')
  }
}

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
})
</script>

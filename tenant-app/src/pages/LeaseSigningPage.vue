<template>
  <q-layout view="hHh lpR fFf">
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" aria-label="Go back" @click="$router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          Lease &amp; Signing
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="page-container">

        <!-- Loading -->
        <div v-if="loading" class="column q-gutter-sm">
          <q-skeleton v-for="i in 2" :key="i" height="120px" class="rounded-borders" />
        </div>

        <!-- No lease -->
        <div v-else-if="!lease" class="empty-state">
          <q-icon name="description" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
          <div class="empty-state-title">No active lease found</div>
          <div class="empty-state-sub">Contact your agent to get started</div>
        </div>

        <template v-else>

          <!-- Lease card -->
          <q-card flat class="q-mb-md">
            <q-card-section>
              <div class="row items-start justify-between">
                <div>
                  <div class="text-weight-semibold">{{ lease.unit_label ?? lease.property_name }}</div>
                  <div class="text-caption text-grey-6 q-mt-xs">{{ lease.start_date }} – {{ lease.end_date }}</div>
                </div>
                <StatusBadge :value="lease.status" variant="lease" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Signing submissions -->
          <template v-if="submissions.length > 0">
            <div class="section-header">Signing Status</div>
            <q-card v-for="sub in submissions" :key="sub.id" flat class="q-mb-md">
              <q-card-section>
                <div class="row items-center justify-between q-mb-sm">
                  <div class="text-weight-semibold">{{ sub.template_name ?? 'Lease Agreement' }}</div>
                  <StatusBadge :value="sub.status" />
                </div>

                <!-- Signers -->
                <q-list dense separator>
                  <q-item v-for="signer in sub.signers" :key="signer.id">
                    <q-item-section avatar>
                      <q-avatar
                        size="28px"
                        :color="signer.status === 'completed' ? 'green-1' : signer.status === 'declined' ? 'red-1' : 'grey-2'"
                      >
                        <q-icon
                          :name="signer.status === 'completed' ? 'check' : signer.status === 'declined' ? 'close' : 'schedule'"
                          :color="signer.status === 'completed' ? 'positive' : signer.status === 'declined' ? 'negative' : 'grey-5'"
                          size="14px"
                        />
                      </q-avatar>
                    </q-item-section>
                    <q-item-section>
                      <q-item-label class="ellipsis">{{ signer.name ?? signer.email }}</q-item-label>
                      <q-item-label caption class="text-capitalize">{{ signer.role?.replace('_', ' ') }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <StatusBadge :value="signer.status" variant="signer" />
                    </q-item-section>
                  </q-item>
                </q-list>

                <!-- Sign button (if my turn) -->
                <q-btn
                  v-if="myPendingSigner(sub)"
                  label="Sign Now"
                  color="primary"
                  no-caps
                  class="full-width q-mt-md"
                  @click="openSigning(sub)"
                />
              </q-card-section>
            </q-card>
          </template>

        </template>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { Capacitor } from '@capacitor/core'
import { usePlatform } from '../composables/usePlatform'
import { useAuthStore } from '../stores/auth'
import StatusBadge from '../components/StatusBadge.vue'
import * as tenantApi from '../services/api'
import type { TenantLease, ESigningSubmission, ESigningSigner } from '../services/api'
import { EMPTY_ICON_SIZE } from '../utils/designTokens'

const auth = useAuthStore()
const $q = useQuasar()
const { isIos, backIcon, headerClass } = usePlatform()

const loading     = ref(true)
const lease       = ref<TenantLease | null>(null)
const submissions = ref<ESigningSubmission[]>([])

function myPendingSigner(sub: ESigningSubmission): ESigningSigner | undefined {
  return sub.signers?.find(s => s.email === auth.user?.email && s.status === 'pending')
}

async function openSigning(sub: ESigningSubmission) {
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
    const leasesRes = await tenantApi.listLeases()
    const leases = leasesRes.data.results ?? leasesRes.data as TenantLease[]
    if ((leases as TenantLease[]).length === 0) return
    lease.value = (leases as TenantLease[])[0]

    const subsRes = await tenantApi.listSubmissions({ lease: lease.value.id })
    submissions.value = subsRes.data.results ?? subsRes.data as ESigningSubmission[]
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load signing details.', icon: 'error' })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped lang="scss">
</style>

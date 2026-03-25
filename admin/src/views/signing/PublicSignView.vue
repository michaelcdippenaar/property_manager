<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <header class="bg-navy text-white px-4 py-4 shadow">
      <h1 class="text-lg font-semibold tracking-tight">Sign document</h1>
      <p v-if="docTitle" class="text-sm text-white/80 mt-1">{{ docTitle }}</p>
      <p v-if="signerLine" class="text-xs text-white/70 mt-0.5">{{ signerLine }}</p>
    </header>

    <div v-if="loading" class="flex-1 flex items-center justify-center p-8">
      <div class="text-gray-500 text-sm">Loading signing page…</div>
    </div>

    <div v-else-if="errorMsg" class="flex-1 flex items-center justify-center p-8">
      <div class="max-w-md text-center rounded-xl border border-red-200 bg-red-50 px-6 py-5 text-red-800 text-sm">
        {{ errorMsg }}
      </div>
    </div>

    <div v-else class="flex-1 flex flex-col min-h-0">
      <iframe
        :src="embedSrc"
        title="Document signing"
        class="w-full flex-1 min-h-[70vh] border-0 bg-white"
        allow="clipboard-write"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const loading = ref(true)
const errorMsg = ref('')
const embedSrc = ref('')
const docTitle = ref('')
const signerName = ref('')
const signerEmail = ref('')

const signerLine = computed(() => {
  const n = signerName.value.trim()
  const e = signerEmail.value.trim()
  if (n && e) return `${n} · ${e}`
  if (n) return n
  if (e) return e
  return ''
})

const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

onMounted(async () => {
  const token = route.params.token as string
  if (!token) {
    errorMsg.value = 'Invalid link.'
    loading.value = false
    return
  }
  try {
    const { data } = await axios.get(`${apiBase}/esigning/public-sign/${token}/`, {
      headers: { Accept: 'application/json' },
    })
    embedSrc.value = data.embed_src
    docTitle.value = data.document_title || ''
    signerName.value = data.signer_name || ''
    signerEmail.value = data.signer_email || ''
  } catch (e: any) {
    const d = e?.response?.data
    errorMsg.value =
      (typeof d?.detail === 'string' && d.detail) ||
      e?.message ||
      'Could not load this signing link.'
  } finally {
    loading.value = false
  }
})
</script>

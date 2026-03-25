<template>
  <div class="p-6 max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-xl font-bold text-gray-900">Lease Templates</h1>
        <p class="text-sm text-gray-500 mt-0.5">Build and manage reusable lease document templates</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-navy text-white rounded-lg hover:bg-navy/90 transition-colors"
          @click="showUpload = true"
        >
          <Plus :size="14" /> New Template
        </button>
      </div>
    </div>

    <!-- Template grid -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="h-28 bg-gray-100 rounded-xl animate-pulse" />
    </div>

    <div v-else-if="!templates.length" class="text-center py-20 text-gray-400">
      <FileSignature :size="40" class="mx-auto mb-3 opacity-30" />
      <p class="font-medium">No templates yet</p>
      <p class="text-sm mt-1">Upload a DOCX or start from scratch</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div
        v-for="tmpl in templates" :key="tmpl.id"
        class="bg-white border border-gray-200 rounded-xl p-4 hover:border-navy/40 hover:shadow-sm transition-all cursor-pointer group"
        @click="router.push({ name: 'lease-template-edit', params: { id: tmpl.id } })"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-2">
            <FileText :size="18" class="text-navy flex-shrink-0" />
            <div>
              <div class="font-semibold text-sm text-gray-900">{{ tmpl.name }}</div>
              <div class="text-xs text-gray-400 mt-0.5">v{{ tmpl.version }}{{ tmpl.province ? ` · ${tmpl.province}` : '' }}</div>
            </div>
          </div>
          <span
            class="text-[10px] px-2 py-0.5 rounded-full font-medium"
            :class="tmpl.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-400'"
          >{{ tmpl.is_active ? 'Active' : 'Inactive' }}</span>
        </div>
        <div class="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <span>{{ tmpl.fields_schema?.length ?? 0 }} fields</span>
          <span v-if="tmpl.content_html" class="text-teal-600">· HTML content</span>
          <span class="ml-auto text-gray-300 group-hover:text-navy transition-colors">Edit →</span>
        </div>
      </div>
    </div>

    <!-- Upload / create modal -->
    <div v-if="showUpload" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="showUpload = false">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-bold text-gray-900">New Lease Template</h2>
          <button class="text-gray-400 hover:text-gray-600" @click="showUpload = false"><X :size="16" /></button>
        </div>

        <div class="space-y-3">
          <div>
            <label class="text-xs font-medium text-gray-600 block mb-1">Template name *</label>
            <input v-model="form.name" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-navy" placeholder="SA Standard Residential Lease" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs font-medium text-gray-600 block mb-1">Version</label>
              <input v-model="form.version" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-navy" placeholder="1.0" />
            </div>
            <div>
              <label class="text-xs font-medium text-gray-600 block mb-1">Province (optional)</label>
              <input v-model="form.province" class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-navy" placeholder="Western Cape" />
            </div>
          </div>
          <div>
            <label class="text-xs font-medium text-gray-600 block mb-1">Upload DOCX or PDF (optional)</label>
            <label class="flex flex-col items-center justify-center w-full h-20 border-2 border-dashed border-gray-200 rounded-lg cursor-pointer hover:border-navy/40 transition-colors text-xs text-gray-400 gap-1">
              <Upload :size="16" />
              <span>{{ form.file ? form.file.name : 'Click to choose file' }}</span>
              <input type="file" class="hidden" accept=".docx,.pdf" @change="onFileChange" />
            </label>
          </div>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700" @click="showUpload = false">Cancel</button>
          <button
            class="px-4 py-2 text-sm font-medium bg-navy text-white rounded-lg hover:bg-navy/90 disabled:opacity-50 transition-colors"
            :disabled="!form.name || creating"
            @click="createTemplate"
          >
            <Loader2 v-if="creating" :size="13" class="inline animate-spin mr-1" />
            {{ creating ? 'Creating…' : 'Create & Open Editor' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { FileSignature, FileText, Plus, X, Upload, Loader2 } from 'lucide-vue-next'
import api from '../../api'

const router = useRouter()
const loading   = ref(true)
const templates = ref<any[]>([])
const showUpload = ref(false)
const creating  = ref(false)

const form = ref({ name: '', version: '1.0', province: '', file: null as File | null })

onMounted(async () => {
  try {
    const { data } = await api.get('/leases/templates/')
    templates.value = data.results ?? data
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function onFileChange(e: Event) {
  form.value.file = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function createTemplate() {
  if (!form.value.name) return
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.value.name)
    fd.append('version', form.value.version || '1.0')
    if (form.value.province) fd.append('province', form.value.province)
    if (form.value.file) fd.append('template_file', form.value.file)
    else {
      // Create without file — upload a minimal placeholder docx
      fd.append('template_file', new Blob([''], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }), 'blank.docx')
    }
    const { data } = await api.post('/leases/templates/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    router.push({ name: 'lease-template-edit', params: { id: data.id } })
  } catch (e: any) {
    alert(e?.response?.data?.error || 'Failed to create template')
  } finally {
    creating.value = false
  }
}
</script>

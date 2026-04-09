<template>
  <div class="flex flex-col h-dvh overflow-hidden bg-surface">
    <AppHeader title="Report a Repair" show-back back-label="Repairs" />

    <div class="scroll-page px-4 pt-6 pb-8 space-y-5">
      <!-- Title -->
      <div>
        <p class="list-section-header px-1 pt-0 pb-1">Title</p>
        <div class="list-section">
          <div class="list-row">
            <input
              v-model="form.title"
              type="text"
              placeholder="e.g. Leaking tap in bathroom"
              class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
            />
          </div>
        </div>
      </div>

      <!-- Category & Priority -->
      <div class="list-section">
        <div class="list-row">
          <span class="text-sm text-gray-500 w-24 flex-shrink-0">Category</span>
          <select v-model="form.category" class="flex-1 text-sm text-gray-900 outline-none bg-transparent appearance-none">
            <option value="">Select…</option>
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <ChevronRight :size="16" class="text-gray-300 flex-shrink-0" />
        </div>
        <div class="list-row">
          <span class="text-sm text-gray-500 w-24 flex-shrink-0">Priority</span>
          <select v-model="form.priority" class="flex-1 text-sm text-gray-900 outline-none bg-transparent appearance-none">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <ChevronRight :size="16" class="text-gray-300 flex-shrink-0" />
        </div>
      </div>

      <!-- Description -->
      <div>
        <p class="list-section-header px-1 pt-0 pb-1">Description</p>
        <div class="list-section">
          <div class="px-5 py-3">
            <textarea
              v-model="form.description"
              rows="4"
              placeholder="Describe the issue in detail…"
              class="w-full text-sm text-gray-900 outline-none bg-transparent resize-none placeholder-gray-400"
            />
          </div>
        </div>
      </div>

      <!-- Error -->
      <p v-if="errorMsg" class="text-danger-600 text-sm text-center">{{ errorMsg }}</p>

      <!-- Submit -->
      <button
        class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base ripple touchable active:scale-[0.98]"
        :disabled="loading"
        @click="submit"
      >
        <span v-if="!loading">Submit Repair Request</span>
        <Loader2 v-else :size="20" class="animate-spin mx-auto" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ChevronRight, Loader2 } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const form = ref({ title: '', category: '', priority: 'medium', description: '' })
const loading = ref(false)
const errorMsg = ref('')

const categories = ['Plumbing', 'Electrical', 'HVAC', 'Appliance', 'Structural', 'Pest Control', 'Cleaning', 'Other']

onMounted(() => {
  // Pre-fill from AI chat draft
  const draft = route.query.title as string
  if (draft) form.value.title = draft
})

async function submit() {
  if (!form.value.title.trim() || !form.value.description.trim()) {
    errorMsg.value = 'Please fill in the title and description.'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await api.post('/maintenance/', form.value)
    toast.success('Repair request submitted!')
    router.replace({ name: 'issue-detail', params: { id: res.data.id } })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail ?? 'Failed to submit. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

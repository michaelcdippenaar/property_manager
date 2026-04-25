<template>
  <div class="card p-5 space-y-5 max-w-3xl">
    <div class="space-y-1">
      <h3 class="font-semibold text-gray-900">AI Domain Knowledge</h3>
      <p class="text-sm text-gray-500">
        Edit the markdown rules that are injected into the AI Guide system prompt on every
        request. Changes are saved to <code class="text-xs bg-gray-100 px-1 rounded">content/ai/knowledge.md</code>
        and take effect immediately (no redeploy required).
      </p>
    </div>

    <div v-if="!isAdmin" class="rounded-lg bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
      Only system administrators can edit AI domain knowledge.
    </div>

    <template v-else>
      <div v-if="loadError" class="rounded-lg bg-danger-50 border border-danger-200 p-4 text-sm text-danger-700 flex items-center gap-2">
        <AlertCircle :size="15" />
        {{ loadError }}
      </div>

      <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 :size="15" class="animate-spin" />
        Loading knowledge file…
      </div>

      <div v-else class="space-y-3">
        <label class="label">Markdown content</label>
        <textarea
          v-model="content"
          class="input font-mono text-xs leading-relaxed"
          rows="24"
          placeholder="# Klikk Domain Rules&#10;&#10;Add rules here in Markdown format."
          spellcheck="false"
          :disabled="saving"
        />
        <p class="text-xs text-gray-400">
          Markdown is rendered for readability — plain text rules also work.
          The full content is injected verbatim into the AI system prompt under
          <code class="bg-gray-100 px-1 rounded">## Klikk Domain Rules</code>.
        </p>
      </div>

      <div v-if="successMsg" class="flex items-center gap-2 text-sm text-success-600">
        <CheckCircle2 :size="15" />
        {{ successMsg }}
      </div>
      <div v-if="saveError" class="flex items-center gap-2 text-sm text-danger-600">
        <AlertCircle :size="15" />
        {{ saveError }}
      </div>

      <button
        class="btn-primary"
        :disabled="saving || loading"
        @click="save"
      >
        <Loader2 v-if="saving" :size="15" class="animate-spin" />
        Save Knowledge File
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loader2, AlertCircle, CheckCircle2 } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { fetchKnowledge, saveKnowledge } from '../../api/ai'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'admin')

const content = ref('')
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const saveError = ref('')
const successMsg = ref('')

onMounted(async () => {
  if (!isAdmin.value) return
  loading.value = true
  loadError.value = ''
  try {
    const data = await fetchKnowledge()
    content.value = data.content
  } catch (e: any) {
    loadError.value = e.response?.data?.detail || 'Failed to load knowledge file.'
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  saveError.value = ''
  successMsg.value = ''
  try {
    await saveKnowledge(content.value)
    successMsg.value = 'Knowledge file saved. AI Guide will use the new rules immediately.'
  } catch (e: any) {
    saveError.value = e.response?.data?.detail || 'Failed to save knowledge file.'
  } finally {
    saving.value = false
  }
}
</script>

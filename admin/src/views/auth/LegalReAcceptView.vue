<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg max-w-lg w-full p-8">
      <!-- Logo / header -->
      <div class="flex items-center gap-3 mb-6">
        <div class="w-10 h-10 rounded-xl bg-[#2B2D6E] flex items-center justify-center">
          <span class="text-white font-bold text-sm">K</span>
        </div>
        <span class="text-[#2B2D6E] font-bold text-xl">Klikk</span>
      </div>

      <h1 class="text-2xl font-bold text-gray-900 mb-2">Updated legal documents</h1>
      <p class="text-gray-500 text-sm mb-6">
        We have updated the following documents. Please review and accept them to continue using
        Klikk.
      </p>

      <!-- Document list -->
      <ul class="space-y-3 mb-8">
        <li
          v-for="doc in auth.pendingLegalDocs"
          :key="doc.id"
          class="flex items-start gap-3 rounded-xl border border-gray-200 p-4"
        >
          <div class="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-[#FF3D7F]/10 flex items-center justify-center">
            <svg class="w-3 h-3 text-[#FF3D7F]" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clip-rule="evenodd"
              />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-gray-900 text-sm">{{ doc.title || doc.doc_type }}</p>
            <p class="text-xs text-gray-400 mt-0.5">Version {{ doc.version }}</p>
          </div>
        </li>
      </ul>

      <!-- Error message -->
      <p v-if="error" class="text-red-600 text-sm mb-4">{{ error }}</p>

      <!-- Accept button -->
      <button
        :disabled="accepting"
        class="w-full rounded-xl bg-[#2B2D6E] text-white font-semibold py-3 text-sm disabled:opacity-60 hover:bg-[#23256a] transition-colors"
        @click="acceptAll"
      >
        <span v-if="accepting">Accepting...</span>
        <span v-else>I have read and accept all updated documents</span>
      </button>

      <p class="text-xs text-gray-400 text-center mt-4">
        By clicking accept, you confirm you have read the updated documents listed above.
        You may view them at
        <a href="https://klikk.co.za/legal/terms" target="_blank" class="underline hover:text-gray-600">klikk.co.za/legal</a>.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const accepting = ref(false)
const error = ref<string | null>(null)

async function acceptAll() {
  accepting.value = true
  error.value = null
  try {
    // Accept each pending doc sequentially; acceptLegalDoc refreshes the list after each
    const docs = [...auth.pendingLegalDocs]
    for (const doc of docs) {
      await auth.acceptLegalDoc(doc.id)
    }
    // All accepted — redirect to the role-appropriate home
    await router.push({ path: auth.homeRoute })
  } catch (e: any) {
    error.value = 'Failed to record acceptance. Please try again.'
  } finally {
    accepting.value = false
  }
}
</script>

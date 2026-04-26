<template>
  <div class="card p-5 space-y-5 max-w-3xl">
    <div class="space-y-1">
      <h3 class="font-semibold text-gray-900">Property Agent</h3>
      <p class="text-sm text-gray-500">Configure your property agent settings here.</p>
    </div>

    <div class="rounded-lg border border-gray-200 p-4 space-y-3">
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 w-9 h-9 rounded-lg bg-navy/5 flex items-center justify-center">
          <Bot :size="18" class="text-navy" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900">AI Assistant</p>
          <p class="text-sm text-gray-500 mt-0.5">
            Ask the AI guide to walk you through configuring your property agent
            settings, or get help with any step in the process.
          </p>
        </div>
      </div>
      <button
        data-testid="open-ai-guide"
        class="btn btn-primary text-sm"
        @click="openAIGuide"
      >
        <Sparkles :size="15" class="mr-1.5" />
        Open AI Guide
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Bot, Sparkles } from 'lucide-vue-next'
import { useAIGuideStore } from '../../stores/aiGuide'

const aiGuideStore = useAIGuideStore()

function openAIGuide() {
  aiGuideStore.open()
}
</script>

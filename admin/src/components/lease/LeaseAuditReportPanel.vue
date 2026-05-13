<template>
  <div class="border border-gray-200 rounded-xl bg-white shadow-sm overflow-hidden">
    <!-- Header -->
    <div
      class="flex items-center gap-3 px-4 py-3 border-b"
      :class="headerBorderClass"
    >
      <!-- Compliance badge -->
      <span
        class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
        :class="badgeClass"
      >
        <component :is="badgeIcon" :size="12" />
        {{ verdictLabel }}
      </span>

      <div class="flex-1 min-w-0">
        <p class="text-xs text-gray-700 leading-snug">{{ report.summary }}</p>
      </div>

      <!-- Dismiss button -->
      <button
        class="flex-shrink-0 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        title="Dismiss audit report"
        @click="emit('dismiss')"
      >
        <X :size="14" />
      </button>
    </div>

    <!-- Finding buckets -->
    <div class="divide-y divide-gray-100">
      <template v-for="(bucket, bucketKey) in findingBuckets" :key="bucketKey">
        <div v-if="bucket.findings.length" class="px-4 py-2">
          <div class="text-micro font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
            {{ bucket.label }}
          </div>
          <div class="space-y-2">
            <div
              v-for="(finding, fi) in bucket.findings"
              :key="fi"
              class="flex gap-2.5 items-start"
            >
              <!-- Severity dot -->
              <span
                class="mt-0.5 flex-shrink-0 w-2 h-2 rounded-full"
                :class="severityDotClass(finding.severity)"
                :title="finding.severity"
              />

              <div class="flex-1 min-w-0">
                <p class="text-xs text-gray-700 leading-snug">{{ finding.message }}</p>

                <div class="flex flex-wrap items-center gap-1.5 mt-1">
                  <!-- Severity badge -->
                  <span
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-micro font-medium"
                    :class="severityBadgeClass(finding.severity)"
                  >
                    {{ severityLabel(finding.severity) }}
                  </span>

                  <!-- Citation -->
                  <span
                    v-if="finding.citation"
                    class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-navy/5 text-navy text-micro font-mono"
                  >
                    <BookOpen :size="8" />
                    {{ finding.citation }}
                  </span>

                  <!-- Confidence chip -->
                  <span
                    class="inline-flex items-center px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 text-micro"
                    :title="`Confidence: ${confidenceLabel(finding.confidence_level)}`"
                  >
                    {{ confidenceLabel(finding.confidence_level) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- No findings fallback -->
      <div
        v-if="totalFindings === 0"
        class="px-4 py-3 text-xs text-gray-400 italic text-center"
      >
        No specific findings — see summary above.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircle2, AlertTriangle, XCircle, X, BookOpen } from 'lucide-vue-next'
import type { AuditReport, ReviewFinding } from '../../composables/useLeaseAIChatV2'

// ── Props ──────────────────────────────────────────────────────────────── //

const props = defineProps<{
  report: AuditReport
}>()

const emit = defineEmits<{
  (e: 'dismiss'): void
}>()

// ── Computed ───────────────────────────────────────────────────────────── //

const verdictLabel = computed(() => {
  switch (props.report.verdict) {
    case 'pass':               return 'PASS'
    case 'revise_recommended': return 'WARNINGS'
    case 'revise_required':    return 'FAIL'
    default:                   return String(props.report.verdict).toUpperCase()
  }
})

const badgeClass = computed(() => {
  switch (props.report.verdict) {
    case 'pass':               return 'bg-success-100 text-success-700 border border-success-200'
    case 'revise_recommended': return 'bg-warning-100 text-warning-700 border border-warning-200'
    case 'revise_required':    return 'bg-danger-100 text-danger-700 border border-danger-200'
    default:                   return 'bg-gray-100 text-gray-600 border border-gray-200'
  }
})

const badgeIcon = computed(() => {
  switch (props.report.verdict) {
    case 'pass':               return CheckCircle2
    case 'revise_recommended': return AlertTriangle
    case 'revise_required':    return XCircle
    default:                   return AlertTriangle
  }
})

const headerBorderClass = computed(() => {
  switch (props.report.verdict) {
    case 'pass':               return 'border-success-100 bg-success-50/30'
    case 'revise_recommended': return 'border-warning-100 bg-warning-50/30'
    case 'revise_required':    return 'border-danger-100 bg-danger-50/30'
    default:                   return 'border-gray-100'
  }
})

interface FindingBucket {
  label: string
  findings: ReviewFinding[]
}

const findingBuckets = computed<Record<string, FindingBucket>>(() => ({
  statute: {
    label: 'Statute findings',
    findings: props.report.statute_findings ?? [],
  },
  case_law: {
    label: 'Case law',
    findings: props.report.case_law_findings ?? [],
  },
  format: {
    label: 'Format',
    findings: props.report.format_findings ?? [],
  },
}))

const totalFindings = computed(() =>
  (props.report.statute_findings?.length ?? 0) +
  (props.report.case_law_findings?.length ?? 0) +
  (props.report.format_findings?.length ?? 0),
)

// ── Helpers ────────────────────────────────────────────────────────────── //

function severityDotClass(severity: ReviewFinding['severity']): string {
  switch (severity) {
    case 'blocking':     return 'bg-danger-500'
    case 'recommended':  return 'bg-warning-500'
    case 'nice_to_have': return 'bg-info-500'
    default:             return 'bg-gray-400'
  }
}

function severityBadgeClass(severity: ReviewFinding['severity']): string {
  switch (severity) {
    case 'blocking':     return 'bg-danger-50 text-danger-700 border border-danger-100'
    case 'recommended':  return 'bg-warning-50 text-warning-700 border border-warning-100'
    case 'nice_to_have': return 'bg-info-50 text-info-700 border border-info-100'
    default:             return 'bg-gray-50 text-gray-600 border border-gray-100'
  }
}

function severityLabel(severity: ReviewFinding['severity']): string {
  switch (severity) {
    case 'blocking':     return 'Blocking'
    case 'recommended':  return 'Recommended'
    case 'nice_to_have': return 'Advisory'
    default:             return severity
  }
}

function confidenceLabel(level: ReviewFinding['confidence_level']): string {
  switch (level) {
    case 'lawyer_reviewed': return 'Lawyer reviewed'
    case 'mc_reviewed':     return 'MC reviewed'
    case 'ai_curated':      return 'AI curated'
    default:                return level
  }
}
</script>

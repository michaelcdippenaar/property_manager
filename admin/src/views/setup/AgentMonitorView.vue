<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">Agent Monitor</h2>
        <p class="text-sm text-gray-500 mt-0.5">AI ecosystem health, usage, and diagnostics</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="runHealthCheck" class="btn btn-ghost text-sm" :disabled="healthLoading">
          <HeartPulse :size="15" class="mr-1" />
          Health Check
        </button>
        <button @click="runProgressiveTest" class="btn btn-primary text-sm" :disabled="testLoading">
          <FlaskConical :size="15" class="mr-1" />
          Run Tests
        </button>
      </div>
    </div>

    <!-- Health Banner -->
    <div
      v-if="health"
      class="rounded-lg px-4 py-3 flex items-center gap-3 text-sm font-medium"
      :class="{
        'bg-green-50 text-green-800 border border-green-200': health.overall === 'healthy',
        'bg-amber-50 text-amber-800 border border-amber-200': health.overall === 'degraded',
        'bg-red-50 text-red-800 border border-red-200': health.overall === 'unhealthy',
      }"
    >
      <component
        :is="health.overall === 'healthy' ? CheckCircle2 : health.overall === 'degraded' ? AlertTriangle : XCircle"
        :size="18"
      />
      System {{ health.overall }}
      <span class="text-xs font-normal ml-2">
        {{ health.checks?.filter((c: any) => c.status === 'pass').length }}/{{ health.checks?.length }} checks passing
      </span>
    </div>

    <!-- Stat Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4" v-if="dashboard">
      <div class="card p-4">
        <div class="text-xs text-gray-500 uppercase tracking-wide">RAG Chunks</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ dashboard.rag?.total_chunks?.toLocaleString() || 0 }}</div>
        <div class="text-xs text-gray-400 mt-1">
          {{ dashboard.rag?.contracts || 0 }} contracts &middot;
          {{ dashboard.rag?.agent_qa || 0 }} Q&A &middot;
          {{ dashboard.rag?.chat_knowledge || 0 }} learned
        </div>
      </div>

      <div class="card p-4 cursor-pointer hover:ring-2 hover:ring-navy/20 transition" @click="activeTab = 'tools'">
        <div class="text-xs text-gray-500 uppercase tracking-wide">MCP Tools</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ registry?.totals?.mcp_tools || dashboard?.mcp?.tool_count || 0 }}</div>
        <div class="text-xs text-gray-400 mt-1">
          {{ registry?.totals?.mcp_resources || dashboard?.mcp?.resource_count || 0 }} resources &middot;
          {{ dashboard?.mcp?.server_exists ? 'Server OK' : 'Not found' }}
        </div>
      </div>

      <div class="card p-4 cursor-pointer hover:ring-2 hover:ring-navy/20 transition" @click="activeTab = 'skills'">
        <div class="text-xs text-gray-500 uppercase tracking-wide">Skills</div>
        <div class="text-2xl font-bold text-navy mt-1">
          {{ (registry?.totals?.claude_skills || 0) + (registry?.totals?.maintenance_skills || dashboard?.skills?.total_active || 0) }}
        </div>
        <div class="text-xs text-gray-400 mt-1">
          {{ registry?.totals?.claude_skills || 0 }} claude &middot;
          {{ registry?.totals?.maintenance_skills || dashboard?.skills?.total_active || 0 }} maintenance
        </div>
      </div>

      <div class="card p-4">
        <div class="text-xs text-gray-500 uppercase tracking-wide">API Calls (7d)</div>
        <div class="text-2xl font-bold text-navy mt-1">{{ dashboard?.token_usage?.total_calls?.toLocaleString() || 0 }}</div>
        <div class="text-xs text-gray-400 mt-1">
          {{ formatTokens(dashboard?.token_usage?.total_input_tokens) }} in &middot;
          {{ formatTokens(dashboard?.token_usage?.total_output_tokens) }} out
        </div>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200">
      <nav class="flex gap-6">
        <button
          v-for="tab in tabs" :key="tab.id"
          @click="activeTab = tab.id"
          class="pb-2 text-sm font-medium border-b-2 transition-colors"
          :class="activeTab === tab.id
            ? 'border-navy text-navy'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- ═══ OVERVIEW TAB ═══ -->
    <div v-if="activeTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- RAG Collections -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Database :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Vectorised Data</span>
          <span
            class="ml-auto text-xs px-2 py-0.5 rounded-full"
            :class="dashboard?.rag?.status === 'healthy' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'"
          >
            {{ dashboard?.rag?.status || 'loading' }}
          </span>
        </div>
        <div class="p-4 space-y-3 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">Embedding Model</span>
            <code class="text-xs bg-gray-100 px-2 py-0.5 rounded">{{ dashboard?.rag?.embedding_model }}</code>
          </div>
          <div class="flex justify-between" v-for="col in ragCollections" :key="col.label">
            <span class="text-gray-500">{{ col.label }}</span>
            <span class="font-mono">{{ col.count?.toLocaleString() }}</span>
          </div>
          <div class="flex justify-between border-t border-gray-100 pt-2">
            <span class="text-gray-500">Source Files</span>
            <span class="font-mono">{{ dashboard?.indexed_data?.source_files || 0 }}</span>
          </div>
          <div class="flex justify-between" v-if="dashboard?.indexed_data?.file_types">
            <span class="text-gray-500">File Types</span>
            <span class="text-xs">
              <span v-for="(count, ext) in dashboard.indexed_data.file_types" :key="ext" class="mr-2">
                {{ ext }} ({{ count }})
              </span>
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Chat Log Entries</span>
            <span class="font-mono">{{ dashboard?.indexed_data?.chat_log_entries || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Agent Endpoints -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Bot :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Agent Endpoints</span>
        </div>
        <div class="divide-y divide-gray-50">
          <div v-for="agent in dashboard?.agents" :key="agent.name" class="px-4 py-3">
            <div class="flex items-center justify-between">
              <div>
                <span class="text-sm font-medium text-gray-900">{{ agent.name }}</span>
                <div class="text-xs text-gray-400 mt-0.5 font-mono">{{ agent.endpoint }}</div>
              </div>
              <span
                class="text-xs px-2 py-0.5 rounded-full"
                :class="agent.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
              >
                {{ agent.status }}
              </span>
            </div>
            <div class="flex gap-1.5 mt-1.5 flex-wrap">
              <span
                v-for="f in agent.features" :key="f"
                class="text-[10px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded"
              >{{ f }}</span>
            </div>
            <div class="text-xs text-gray-400 mt-1">
              {{ agent.model }} &middot; {{ agent.rate_limit }}
            </div>
          </div>
        </div>
      </div>

      <!-- Token Usage -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Coins :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Token Usage (7 days)</span>
        </div>
        <div class="p-4 space-y-3 text-sm">
          <div class="grid grid-cols-3 gap-3">
            <div class="text-center">
              <div class="text-lg font-bold text-navy">{{ formatTokens(dashboard?.token_usage?.total_input_tokens) }}</div>
              <div class="text-xs text-gray-400">Input</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-navy">{{ formatTokens(dashboard?.token_usage?.total_output_tokens) }}</div>
              <div class="text-xs text-gray-400">Output</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-navy">{{ dashboard?.token_usage?.total_calls || 0 }}</div>
              <div class="text-xs text-gray-400">Calls</div>
            </div>
          </div>

          <div class="text-xs text-gray-500 mt-3">Per Endpoint</div>
          <div class="divide-y divide-gray-50">
            <div v-for="ep in dashboard?.token_usage?.by_endpoint" :key="ep.endpoint" class="py-2 flex justify-between items-center">
              <div>
                <span class="text-sm font-medium text-gray-700">{{ ep.endpoint }}</span>
                <div class="text-xs text-gray-400">{{ ep.calls }} calls</div>
              </div>
              <div class="text-right">
                <div class="text-xs font-mono">{{ formatTokens(ep.total_input) }} in</div>
                <div class="text-xs font-mono text-gray-400">avg {{ formatTokens(ep.avg_input) }}</div>
                <div
                  v-if="(ep.peak_input || 0) > 50000"
                  class="text-[10px] text-red-600 font-medium mt-0.5"
                >
                  !! Max {{ formatTokens(ep.peak_input) }} — oversized context
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="dashboard?.token_usage?.oversized_context_alerts?.length"
            class="bg-red-50 border border-red-200 rounded-lg p-3 mt-3"
          >
            <div class="text-xs font-medium text-red-700 flex items-center gap-1">
              <AlertTriangle :size="13" /> Oversized Context Detected
            </div>
            <div class="text-xs text-red-600 mt-1">
              {{ dashboard.token_usage.oversized_context_alerts.length }} endpoint(s) sending &gt;50k input tokens.
              Review RAG chunk counts and transcript windowing.
            </div>
          </div>
        </div>
      </div>

      <!-- System Info -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Settings :size="16" class="text-navy" />
          <span class="font-semibold text-sm">System Config</span>
        </div>
        <div class="p-4 space-y-2 text-sm">
          <div v-for="(val, key) in dashboard?.system" :key="key" class="flex justify-between">
            <span class="text-gray-500">{{ formatKey(key) }}</span>
            <span :class="typeof val === 'boolean' ? (val ? 'text-green-600' : 'text-gray-400') : 'text-gray-700'">
              {{ typeof val === 'boolean' ? (val ? 'Yes' : 'No') : val }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ TOOLS TAB ═══ -->
    <div v-if="activeTab === 'tools'">
      <!-- Endpoint Usage Summary -->
      <div v-if="registry?.endpoint_usage" class="card mb-4">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Coins :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Agent Usage (30 days)</span>
          <span class="ml-auto text-sm font-bold text-navy">{{ registry.total_ai_calls_30d || 0 }} total calls</span>
        </div>
        <div class="p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <div v-for="(info, key) in registry.endpoint_usage" :key="key" class="text-center p-3 bg-gray-50 rounded-lg">
            <div class="text-lg font-bold text-navy">{{ info.calls_30d }}</div>
            <div class="text-[10px] text-gray-500 mt-0.5">{{ info.label }}</div>
          </div>
        </div>
      </div>

      <!-- MCP Tools Grid -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Plug :size="16" class="text-navy" />
          <span class="font-semibold text-sm">MCP Tools</span>
          <span class="ml-auto text-xs text-gray-400">{{ registry?.mcp_tools?.length || 0 }} tools</span>
        </div>
        <div class="p-4">
          <!-- Category filter -->
          <div class="flex gap-2 mb-4 flex-wrap">
            <button
              v-for="cat in toolCategories" :key="cat"
              @click="toolFilter = toolFilter === cat ? '' : cat"
              class="text-xs px-2.5 py-1 rounded-full border transition-colors"
              :class="toolFilter === cat
                ? 'bg-navy text-white border-navy'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'"
            >
              {{ cat }}
              <span class="ml-1 opacity-60">{{ filteredTools.filter((t: any) => t.category === cat).length || toolsByCategory(cat).length }}</span>
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            <div
              v-for="tool in displayedTools" :key="tool.id"
              @click="selectedTool = tool"
              class="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-indigo-50 hover:ring-1 hover:ring-indigo-200 transition group"
            >
              <div class="flex items-start justify-between">
                <span class="text-sm font-medium text-gray-800 group-hover:text-navy">{{ tool.name }}</span>
                <span class="text-[10px] bg-white text-gray-400 px-1.5 py-0.5 rounded border border-gray-100">{{ tool.category }}</span>
              </div>
              <p class="text-xs text-gray-500 mt-1 line-clamp-2">{{ tool.description }}</p>
              <div class="flex gap-1 mt-2" v-if="tool.parameters?.length">
                <span
                  v-for="p in tool.parameters.slice(0, 3)" :key="p"
                  class="text-[10px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded"
                >{{ p }}</span>
                <span v-if="tool.parameters.length > 3" class="text-[10px] text-gray-400">+{{ tool.parameters.length - 3 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- MCP Resources -->
      <div class="card mt-4">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Database :size="16" class="text-navy" />
          <span class="font-semibold text-sm">MCP Resources</span>
        </div>
        <div class="p-4 space-y-2">
          <div
            v-for="res in registry?.mcp_resources" :key="res.uri"
            class="flex items-center gap-3 p-2 bg-gray-50 rounded"
          >
            <code class="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{{ res.uri }}</code>
            <span class="text-xs text-gray-500">{{ res.description }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ SKILLS TAB ═══ -->
    <div v-if="activeTab === 'skills'">
      <!-- Claude Skills -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Sparkles :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Claude Code Skills</span>
          <span class="ml-auto text-xs text-gray-400">{{ registry?.claude_skills?.length || 0 }} skills</span>
        </div>
        <div class="divide-y divide-gray-50">
          <div
            v-for="skill in registry?.claude_skills" :key="skill.id"
            @click="selectedSkill = skill"
            class="px-4 py-3 cursor-pointer hover:bg-indigo-50 transition group"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800 group-hover:text-navy">{{ skill.title }}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded-full"
                  :class="{
                    'bg-blue-100 text-blue-700': skill.category === 'lease',
                    'bg-red-100 text-red-700': skill.category === 'security',
                    'bg-purple-100 text-purple-700': skill.category === 'esigning',
                    'bg-gray-100 text-gray-600': skill.category === 'general',
                  }"
                >{{ skill.category }}</span>
              </div>
              <ChevronRight :size="14" class="text-gray-300 group-hover:text-navy" />
            </div>
            <p class="text-xs text-gray-500 mt-1 line-clamp-2">{{ skill.description }}</p>
            <div class="flex gap-2 mt-1.5 text-[10px] text-gray-400">
              <span v-if="skill.steps">{{ skill.steps }} steps</span>
              <span v-if="skill.references?.length">{{ skill.references.length }} reference{{ skill.references.length > 1 ? 's' : '' }}</span>
              <span class="font-mono">{{ skill.path }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Maintenance Skills -->
      <div class="card mt-4">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Wrench :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Maintenance Skills</span>
          <span class="ml-auto text-xs text-gray-400">{{ registry?.maintenance_skills?.length || 0 }} skills</span>
        </div>

        <!-- Trade filter -->
        <div class="px-4 pt-3 flex gap-2 flex-wrap">
          <button
            v-for="trade in maintenanceTrades" :key="trade"
            @click="tradeFilter = tradeFilter === trade ? '' : trade"
            class="text-xs px-2.5 py-1 rounded-full border transition-colors capitalize"
            :class="tradeFilter === trade
              ? 'bg-navy text-white border-navy'
              : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'"
          >
            {{ trade }}
          </button>
        </div>

        <div class="divide-y divide-gray-50 mt-2">
          <div
            v-for="skill in filteredMaintenanceSkills" :key="skill.id"
            @click="selectedMaintSkill = skill"
            class="px-4 py-3 cursor-pointer hover:bg-indigo-50 transition group"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-800 group-hover:text-navy">{{ skill.name }}</span>
                <span class="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full capitalize">{{ skill.trade }}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded-full"
                  :class="{
                    'bg-green-100 text-green-700': skill.difficulty === 'easy',
                    'bg-amber-100 text-amber-700': skill.difficulty === 'medium',
                    'bg-red-100 text-red-700': skill.difficulty === 'hard',
                  }"
                >{{ skill.difficulty }}</span>
              </div>
              <ChevronRight :size="14" class="text-gray-300 group-hover:text-navy" />
            </div>
            <p class="text-xs text-gray-500 mt-1">{{ skill.description }}</p>
            <div class="flex gap-1 mt-1.5 flex-wrap" v-if="skill.symptom_phrases?.length">
              <span
                v-for="phrase in skill.symptom_phrases.slice(0, 4)" :key="phrase"
                class="text-[10px] bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded"
              >{{ phrase }}</span>
              <span v-if="skill.symptom_phrases.length > 4" class="text-[10px] text-gray-400">+{{ skill.symptom_phrases.length - 4 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Skills by Trade chart -->
      <div class="card mt-4">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <BookOpen :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Skills by Trade</span>
        </div>
        <div class="p-4">
          <div v-if="dashboard?.skills?.by_trade" class="space-y-2">
            <div v-for="(count, trade) in dashboard.skills.by_trade" :key="trade" class="flex items-center gap-3">
              <span class="text-sm text-gray-700 w-24 truncate capitalize">{{ trade }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-3">
                <div
                  class="bg-navy rounded-full h-3 transition-all"
                  :style="{ width: `${Math.min(100, (count / maxSkillCount) * 100)}%` }"
                />
              </div>
              <span class="text-xs text-gray-500 w-8 text-right">{{ count }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-gray-400">No skills configured</div>
        </div>
      </div>
    </div>

    <!-- ═══ DIAGNOSTICS TAB ═══ -->
    <div v-if="activeTab === 'diagnostics'" class="space-y-4">
      <!-- Health Check Details -->
      <div v-if="health?.checks" class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <HeartPulse :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Health Check Results</span>
        </div>
        <div class="divide-y divide-gray-50">
          <div v-for="check in health.checks" :key="check.name" class="px-4 py-2.5 flex items-center gap-3">
            <component
              :is="check.status === 'pass' ? CheckCircle2 : check.status === 'warn' ? AlertTriangle : XCircle"
              :size="15"
              :class="{
                'text-green-500': check.status === 'pass',
                'text-amber-500': check.status === 'warn',
                'text-red-500': check.status === 'fail',
              }"
            />
            <span class="text-sm text-gray-700">{{ check.name }}</span>
            <span v-if="check.detail" class="text-xs text-gray-400 ml-auto">{{ check.detail }}</span>
          </div>
        </div>
      </div>
      <div v-else class="card p-8 text-center text-gray-400 text-sm">
        Run a health check to see diagnostic results
      </div>

      <!-- Progressive Test Results -->
      <div v-if="testResult" class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <FlaskConical :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Progressive Test — Level {{ testResult.level }}</span>
          <span
            class="ml-auto text-sm font-bold"
            :class="testResult.score >= 80 ? 'text-green-600' : testResult.score >= 50 ? 'text-amber-600' : 'text-red-600'"
          >
            {{ testResult.score }}%
          </span>
        </div>
        <div class="p-4">
          <div v-if="testResult.comparison" class="mb-4 p-3 rounded-lg text-sm"
            :class="testResult.comparison.improvement >= 0 ? 'bg-green-50' : 'bg-red-50'"
          >
            <span v-if="testResult.comparison.improvement > 0" class="text-green-700 font-medium">
              +{{ testResult.comparison.improvement }}% improvement
            </span>
            <span v-else-if="testResult.comparison.improvement === 0" class="text-gray-600">
              No change from previous run
            </span>
            <span v-else class="text-red-700 font-medium">
              {{ testResult.comparison.improvement }}% regression
            </span>
            <span class="text-xs text-gray-500 ml-2">
              vs Level {{ testResult.comparison.previous_level }} ({{ testResult.comparison.previous_score }}%)
            </span>
          </div>

          <div class="space-y-1.5">
            <div v-for="test in testResult.tests" :key="test.name" class="flex items-center gap-2 text-sm">
              <component :is="test.passed ? CheckCircle2 : XCircle" :size="14"
                :class="test.passed ? 'text-green-500' : 'text-red-500'"
              />
              <span class="text-gray-700">{{ test.name }}</span>
              <span v-if="test.detail" class="text-xs text-gray-400 ml-auto">{{ test.detail }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Test History -->
      <div v-if="testHistory.length" class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <History :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Test History</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Level</th>
                <th>Score</th>
                <th>Tests</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in testHistory.slice().reverse()" :key="run.timestamp">
                <td class="text-xs">{{ formatDate(run.timestamp) }}</td>
                <td>{{ run.level }}</td>
                <td>
                  <span :class="run.score >= 80 ? 'text-green-600' : run.score >= 50 ? 'text-amber-600' : 'text-red-600'" class="font-bold">
                    {{ run.score }}%
                  </span>
                </td>
                <td class="text-xs text-gray-500">{{ run.tests?.length || '?' }} tests</td>
                <td>
                  <span v-if="run.comparison" :class="run.comparison.improvement >= 0 ? 'text-green-600' : 'text-red-600'" class="text-xs font-medium">
                    {{ run.comparison.improvement >= 0 ? '+' : '' }}{{ run.comparison.improvement }}%
                  </span>
                  <span v-else class="text-xs text-gray-400">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Token Usage Log -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Coins :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Recent API Calls</span>
          <button @click="loadTokenLogs" class="ml-auto text-xs text-navy hover:underline">Refresh</button>
        </div>
        <div v-if="tokenLogs.length" class="divide-y divide-gray-50 max-h-[500px] overflow-y-auto">
          <div
            v-for="log in tokenLogs" :key="log.id"
            class="px-4 py-3 cursor-pointer hover:bg-gray-50 transition"
            @click="selectedLog = selectedLog?.id === log.id ? null : log"
          >
            <div class="flex items-center gap-3 text-sm">
              <span class="font-mono text-xs px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700">{{ log.endpoint }}</span>
              <span class="text-gray-500">{{ log.model }}</span>
              <span class="ml-auto flex items-center gap-3 text-xs text-gray-400">
                <span>{{ formatTokens(log.input_tokens) }} in</span>
                <span>{{ formatTokens(log.output_tokens) }} out</span>
                <span :class="log.latency_ms > 5000 ? 'text-red-500 font-medium' : log.latency_ms > 3000 ? 'text-amber-500' : 'text-green-600'">
                  {{ (log.latency_ms / 1000).toFixed(1) }}s
                </span>
                <span>{{ formatDate(log.created_at) }}</span>
              </span>
            </div>
            <!-- Expanded detail -->
            <div v-if="selectedLog?.id === log.id" class="mt-3 p-3 bg-gray-50 rounded-lg text-xs space-y-2">
              <div v-if="log.metadata?.user_message" class="space-y-1">
                <div class="font-semibold text-gray-600">User Message</div>
                <div class="text-gray-700 bg-white p-2 rounded border border-gray-200">{{ log.metadata.user_message }}</div>
              </div>
              <div v-if="log.metadata?.raw_ai_response" class="space-y-1">
                <div class="font-semibold text-gray-600">AI Response (raw)</div>
                <div class="text-gray-700 bg-white p-2 rounded border border-gray-200 whitespace-pre-wrap max-h-40 overflow-y-auto">{{ log.metadata.raw_ai_response }}</div>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div class="bg-white p-2 rounded border border-gray-200">
                  <div class="text-gray-400">System Prompt</div>
                  <div class="font-mono font-medium">{{ formatTokens(log.metadata?.system_prompt_len || 0) }} chars</div>
                </div>
                <div class="bg-white p-2 rounded border border-gray-200">
                  <div class="text-gray-400">RAG Contracts</div>
                  <div class="font-mono font-medium">{{ formatTokens(log.metadata?.rag_contracts_len || 0) }} chars</div>
                </div>
                <div class="bg-white p-2 rounded border border-gray-200">
                  <div class="text-gray-400">RAG Q&amp;A</div>
                  <div class="font-mono font-medium">{{ formatTokens(log.metadata?.rag_qa_len || 0) }} chars</div>
                </div>
                <div class="bg-white p-2 rounded border border-gray-200">
                  <div class="text-gray-400">RAG Issues</div>
                  <div class="font-mono font-medium">{{ formatTokens(log.metadata?.rag_issues_len || 0) }} chars</div>
                </div>
              </div>
              <div class="flex gap-4 text-gray-500">
                <span>Messages in window: {{ log.metadata?.message_count || '?' }}</span>
                <span>Session: #{{ log.metadata?.session_id || '?' }}</span>
                <span v-if="log.metadata?.property_id">Property: #{{ log.metadata.property_id }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="p-8 text-center text-gray-400 text-sm">
          No API calls logged yet
        </div>
      </div>
    </div>

    <!-- ═══ MAINTENANCE TAB ═══ -->
    <div v-if="activeTab === 'maintenance'" class="space-y-4">
      <!-- ═══ TRAINING CHATBOT ═══ -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <Bot :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Maintenance Chatbot</span>
          <span class="text-xs text-gray-400 ml-1">— test &amp; train the AI agent</span>
          <button
            v-if="chatMessages.length > 0"
            @click="chatMessages = []; chatSessionId = null"
            class="ml-auto text-xs text-gray-400 hover:text-red-500 transition"
          >Clear</button>
        </div>
        <div ref="chatContainer" class="p-4 space-y-3 max-h-[400px] overflow-y-auto bg-gray-50/50">
          <div v-if="chatMessages.length === 0" class="py-8 text-center text-gray-400 text-sm">
            Send a message to test the tenant maintenance chatbot.<br>
            <span class="text-xs">Uses the Tenant AI Chat endpoint — same flow as the mobile app.</span>
          </div>
          <div
            v-for="(msg, i) in chatMessages" :key="i"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <!-- Ticket confirmation prompt -->
            <div
              v-if="msg.type === 'confirm'"
              class="max-w-[85%] bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 text-sm space-y-2 rounded-bl-sm"
            >
              <div class="flex items-center gap-1.5 text-amber-700 font-semibold text-xs uppercase tracking-wide">
                <AlertTriangle :size="12" />
                Maintenance identified
              </div>
              <p class="text-gray-800">{{ msg.content }}</p>
              <div v-if="!msg.resolved" class="flex gap-2 pt-0.5">
                <button
                  @click="confirmTicket(msg, true)"
                  class="btn btn-primary text-xs px-3 py-1.5"
                >Yes, log ticket</button>
                <button
                  @click="confirmTicket(msg, false)"
                  class="text-xs px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
                >No, skip</button>
              </div>
              <div v-else class="text-xs text-gray-500 italic flex items-center gap-1.5">
                <CheckCircle2 v-if="msg.resolvedText?.startsWith('Ticket')" :size="12" class="text-green-500" />
                {{ msg.resolvedText }}
              </div>
            </div>
            <div
              v-else-if="msg.type === 'skills'"
              class="max-w-[90%] bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-2.5 text-sm space-y-2 rounded-bl-sm"
            >
              <div class="flex items-center gap-1.5 text-indigo-700 font-semibold text-xs uppercase tracking-wide">
                <BookOpen :size="12" />
                Skills used in chat
              </div>
              <p class="text-gray-800">{{ msg.content }}</p>
              <div v-if="msg.skillsUsed?.preview?.length" class="space-y-1">
                <div
                  v-for="(skillLine, idx) in msg.skillsUsed.preview" :key="`${idx}-${skillLine}`"
                  class="text-xs text-gray-700 bg-white/80 border border-indigo-100 rounded px-2 py-1 font-mono break-words"
                >{{ skillLine }}</div>
              </div>
            </div>
            <!-- Regular message -->
            <div
              v-else
              class="max-w-[80%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap"
              :class="msg.role === 'user'
                ? 'bg-navy text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'"
            >{{ msg.content }}</div>
          </div>
          <div v-if="chatSending" class="flex justify-start">
            <div class="bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-400">
              <span class="inline-flex gap-1">
                <span class="animate-bounce" style="animation-delay: 0ms">.</span>
                <span class="animate-bounce" style="animation-delay: 150ms">.</span>
                <span class="animate-bounce" style="animation-delay: 300ms">.</span>
              </span>
            </div>
          </div>
        </div>
        <div class="px-4 py-3 border-t border-gray-100 flex gap-2">
          <input
            v-model="chatInput"
            @keydown.enter.prevent="sendChatMessage"
            :disabled="chatSending"
            type="text"
            class="input text-sm flex-1"
            placeholder="Ask the maintenance AI agent..."
          />
          <button
            @click="sendChatMessage"
            :disabled="chatSending || !chatInput.trim()"
            class="btn btn-primary text-sm px-4"
          >Send</button>
        </div>
      </div>

      <!-- Chat log controls -->
      <div class="flex items-center gap-3">
        <select v-model="chatLogDays" @change="loadChatLog()" class="input text-sm w-32">
          <option :value="1">Last 24h</option>
          <option :value="7">Last 7 days</option>
          <option :value="30">Last 30 days</option>
        </select>
        <select v-model="chatLogSource" @change="loadChatLog()" class="input text-sm w-32">
          <option value="">All sources</option>
          <option value="ai_agent">AI only</option>
          <option value="user">Users only</option>
        </select>
        <select v-model="chatLogRequest" @change="loadChatLog()" class="input text-sm flex-1">
          <option value="">All requests</option>
          <option v-for="r in chatLogData?.active_requests" :key="r.request_id" :value="r.request_id">
            #{{ r.request_id }} — {{ r.title }} ({{ r.message_count }} msgs)
          </option>
        </select>
      </div>

      <!-- Summary cards -->
      <div v-if="chatLogData?.summary" class="grid grid-cols-3 gap-4">
        <div class="card p-4 text-center">
          <div class="text-2xl font-bold text-navy">{{ chatLogData.summary.total_messages }}</div>
          <div class="text-xs text-gray-400">Total Messages</div>
        </div>
        <div class="card p-4 text-center">
          <div class="text-2xl font-bold text-indigo-600">{{ chatLogData.summary.ai_messages }}</div>
          <div class="text-xs text-gray-400">AI Messages</div>
        </div>
        <div class="card p-4 text-center">
          <div class="text-2xl font-bold text-gray-600">{{ chatLogData.summary.user_messages }}</div>
          <div class="text-xs text-gray-400">User Messages</div>
        </div>
      </div>

      <!-- Chat log entries -->
      <div class="card">
        <div class="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
          <MessageSquare :size="16" class="text-navy" />
          <span class="font-semibold text-sm">Chat Activity Log</span>
          <span class="ml-auto text-xs text-gray-400">{{ chatLogData?.count || 0 }} entries</span>
        </div>
        <div class="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
          <div
            v-for="entry in chatLogData?.entries" :key="entry.id"
            class="px-4 py-3"
            :class="entry.is_ai ? 'bg-indigo-50/40' : ''"
          >
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-medium" :class="entry.is_ai ? 'text-indigo-600' : 'text-gray-700'">
                {{ entry.author }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded-full"
                :class="entry.is_ai ? 'bg-indigo-100 text-indigo-600' : 'bg-gray-100 text-gray-500'"
              >{{ entry.role }}</span>
              <span class="text-[10px] bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded">{{ entry.activity_type }}</span>
              <span class="ml-auto text-[10px] text-gray-400">
                #{{ entry.request_id }} &middot; {{ formatDate(entry.created_at) }}
              </span>
            </div>
            <p class="text-sm text-gray-700 line-clamp-3">{{ entry.message }}</p>
            <div class="text-[10px] text-gray-400 mt-0.5">{{ entry.request_title }}</div>
          </div>
          <div v-if="!chatLogData?.entries?.length" class="p-8 text-center text-gray-400 text-sm">
            No chat activity in this period
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ TOOL DETAIL MODAL ═══ -->
    <div v-if="selectedTool" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="selectedTool = null">
      <div class="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 class="font-semibold text-gray-900">{{ selectedTool.name }}</h3>
            <span class="text-xs text-gray-400">MCP Tool</span>
          </div>
          <button @click="selectedTool = null" class="p-1 rounded-lg hover:bg-gray-100">
            <X :size="18" class="text-gray-400" />
          </button>
        </div>
        <div class="p-5 space-y-4">
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Category</div>
            <span class="text-sm px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full">{{ selectedTool.category }}</span>
          </div>
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Description</div>
            <p class="text-sm text-gray-700">{{ selectedTool.description }}</p>
          </div>
          <div v-if="selectedTool.parameters?.length">
            <div class="text-xs font-medium text-gray-500 uppercase mb-2">Parameters</div>
            <div class="space-y-1">
              <div v-for="p in selectedTool.parameters" :key="p" class="flex items-center gap-2">
                <code class="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">{{ p }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ CLAUDE SKILL DETAIL MODAL ═══ -->
    <div v-if="selectedSkill" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="selectedSkill = null">
      <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <h3 class="font-semibold text-gray-900">{{ selectedSkill.title }}</h3>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-xs px-2 py-0.5 rounded-full"
                :class="{
                  'bg-blue-100 text-blue-700': selectedSkill.category === 'lease',
                  'bg-red-100 text-red-700': selectedSkill.category === 'security',
                  'bg-purple-100 text-purple-700': selectedSkill.category === 'esigning',
                  'bg-gray-100 text-gray-600': selectedSkill.category === 'general',
                }"
              >{{ selectedSkill.category }}</span>
              <span class="text-xs text-gray-400">Claude Code Skill</span>
            </div>
          </div>
          <button @click="selectedSkill = null" class="p-1 rounded-lg hover:bg-gray-100">
            <X :size="18" class="text-gray-400" />
          </button>
        </div>
        <div class="p-5 space-y-4">
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Description</div>
            <p class="text-sm text-gray-700">{{ selectedSkill.description }}</p>
          </div>
          <div class="flex gap-4 text-sm">
            <div v-if="selectedSkill.steps">
              <span class="text-gray-500">Steps:</span>
              <span class="font-medium ml-1">{{ selectedSkill.steps }}</span>
            </div>
            <div v-if="selectedSkill.references?.length">
              <span class="text-gray-500">References:</span>
              <span class="font-medium ml-1">{{ selectedSkill.references.join(', ') }}</span>
            </div>
          </div>
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Source Path</div>
            <code class="text-xs bg-gray-100 px-2 py-1 rounded block">{{ selectedSkill.path }}</code>
          </div>
          <div v-if="selectedSkill.body">
            <div class="text-xs font-medium text-gray-500 uppercase mb-2">Skill Definition</div>
            <pre class="text-xs bg-gray-50 border border-gray-100 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto font-mono leading-relaxed text-gray-700">{{ selectedSkill.body }}</pre>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ MAINTENANCE SKILL DETAIL MODAL ═══ -->
    <div v-if="selectedMaintSkill" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30" @click.self="selectedMaintSkill = null">
      <div class="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 class="font-semibold text-gray-900">{{ selectedMaintSkill.name }}</h3>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">{{ selectedMaintSkill.trade }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full"
                :class="{
                  'bg-green-100 text-green-700': selectedMaintSkill.difficulty === 'easy',
                  'bg-amber-100 text-amber-700': selectedMaintSkill.difficulty === 'medium',
                  'bg-red-100 text-red-700': selectedMaintSkill.difficulty === 'hard',
                }"
              >{{ selectedMaintSkill.difficulty }}</span>
            </div>
          </div>
          <button @click="selectedMaintSkill = null" class="p-1 rounded-lg hover:bg-gray-100">
            <X :size="18" class="text-gray-400" />
          </button>
        </div>
        <div class="p-5 space-y-4">
          <div>
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Description</div>
            <p class="text-sm text-gray-700">{{ selectedMaintSkill.description }}</p>
          </div>
          <div v-if="selectedMaintSkill.symptom_phrases?.length">
            <div class="text-xs font-medium text-gray-500 uppercase mb-2">Symptom Phrases</div>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="p in selectedMaintSkill.symptom_phrases" :key="p"
                class="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full"
              >{{ p }}</span>
            </div>
          </div>
          <div v-if="selectedMaintSkill.steps?.length">
            <div class="text-xs font-medium text-gray-500 uppercase mb-2">Resolution Steps</div>
            <ol class="space-y-1.5 text-sm text-gray-700">
              <li v-for="(step, i) in selectedMaintSkill.steps" :key="i" class="flex gap-2">
                <span class="text-xs font-bold text-navy mt-0.5">{{ i + 1 }}.</span>
                <span>{{ step }}</span>
              </li>
            </ol>
          </div>
          <div v-if="selectedMaintSkill.notes">
            <div class="text-xs font-medium text-gray-500 uppercase mb-1">Notes</div>
            <p class="text-sm text-gray-600">{{ selectedMaintSkill.notes }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-navy"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import {
  Database, Bot, Plug, Coins, BookOpen, Settings, HeartPulse, FlaskConical,
  CheckCircle2, AlertTriangle, XCircle, History, ChevronRight, X, Sparkles, Wrench,
  MessageSquare,
} from 'lucide-vue-next'

const auth = useAuthStore()

const loading = ref(false)
const healthLoading = ref(false)
const testLoading = ref(false)

const dashboard = ref<any>(null)
const health = ref<any>(null)
const testResult = ref<any>(null)
const testHistory = ref<any[]>([])
const registry = ref<any>(null)

// Tab state
const activeTab = ref('overview')
const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'tools', label: 'Tools' },
  { id: 'skills', label: 'Skills' },
  { id: 'maintenance', label: 'Maintenance' },
  { id: 'diagnostics', label: 'Diagnostics' },
]

// Filters
const toolFilter = ref('')
const tradeFilter = ref('')

// Chat log
const chatLogDays = ref(7)
const chatLogSource = ref('')
const chatLogRequest = ref('')
const chatLogData = ref<any>(null)

// Training chatbot (uses tenant chat endpoint)
const chatContainer = ref<HTMLElement | null>(null)
const chatInput = ref('')
const chatSending = ref(false)

interface ChatMessage {
  role: string
  content: string
  type?: 'confirm' | 'skills'
  resolved?: boolean
  resolvedText?: string
  severity?: string
  userMessage?: string
  skillsUsed?: {
    used: boolean
    count: number
    preview: string[]
    source?: string
  }
}
const chatMessages = ref<ChatMessage[]>([])
const chatSessionId = ref<number | null>(null)

// Detail modals
const selectedTool = ref<any>(null)
const selectedSkill = ref<any>(null)
const selectedMaintSkill = ref<any>(null)

// Token logs
const tokenLogs = ref<any[]>([])
const selectedLog = ref<any>(null)

const ragCollections = computed(() => {
  if (!dashboard.value?.rag) return []
  return [
    { label: 'Contract Chunks', count: dashboard.value.rag.contracts },
    { label: 'Agent Q&A', count: dashboard.value.rag.agent_qa },
    { label: 'Chat Knowledge', count: dashboard.value.rag.chat_knowledge },
    { label: 'Maintenance Issues', count: dashboard.value.rag.maintenance_issues },
  ]
})

const maxSkillCount = computed(() => {
  if (!dashboard.value?.skills?.by_trade) return 1
  const counts = Object.values(dashboard.value.skills.by_trade) as number[]
  return Math.max(1, ...counts)
})

const toolCategories = computed(() => {
  const tools = registry.value?.mcp_tools || []
  return [...new Set(tools.map((t: any) => t.category))] as string[]
})

const filteredTools = computed(() => {
  const tools = registry.value?.mcp_tools || []
  if (!toolFilter.value) return tools
  return tools.filter((t: any) => t.category === toolFilter.value)
})

const displayedTools = computed(() => filteredTools.value)

const maintenanceTrades = computed(() => {
  const skills = registry.value?.maintenance_skills || []
  return [...new Set(skills.map((s: any) => s.trade))] as string[]
})

const filteredMaintenanceSkills = computed(() => {
  const skills = registry.value?.maintenance_skills || []
  if (!tradeFilter.value) return skills
  return skills.filter((s: any) => s.trade === tradeFilter.value)
})

function toolsByCategory(cat: string) {
  return (registry.value?.mcp_tools || []).filter((t: any) => t.category === cat)
}

function formatTokens(n: number | undefined): string {
  if (!n) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-ZA', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const { data } = await api.get('/maintenance/monitor/dashboard/')
    dashboard.value = data
  } catch (e: any) {
    console.error('Monitor dashboard error:', e)
  } finally {
    loading.value = false
  }
}

async function loadTokenLogs() {
  try {
    const { data } = await api.get('/maintenance/monitor/token-logs/', { params: { days: 7 } })
    tokenLogs.value = data.logs || []
  } catch (e: any) {
    console.error('Token logs error:', e)
  }
}

async function loadChatLog() {
  try {
    const params: any = { days: chatLogDays.value }
    if (chatLogSource.value) params.source = chatLogSource.value
    if (chatLogRequest.value) params.request_id = chatLogRequest.value
    const { data } = await api.get('/maintenance/monitor/chat-log/', { params })
    chatLogData.value = data
  } catch (e: any) {
    console.error('Chat log error:', e)
  }
}

async function loadRegistry() {
  try {
    const { data } = await api.get('/ai/registry/')
    registry.value = data
  } catch (e: any) {
    console.error('Skills registry error:', e)
  }
}

async function runHealthCheck() {
  healthLoading.value = true
  try {
    const { data } = await api.get('/maintenance/monitor/health/')
    health.value = data
    activeTab.value = 'diagnostics'
  } catch (e: any) {
    console.error('Health check error:', e)
  } finally {
    healthLoading.value = false
  }
}

async function runProgressiveTest() {
  testLoading.value = true
  try {
    const { data } = await api.post('/maintenance/monitor/tests/')
    testResult.value = data
    await loadTestHistory()
    activeTab.value = 'diagnostics'
  } catch (e: any) {
    console.error('Progressive test error:', e)
  } finally {
    testLoading.value = false
  }
}

async function loadTestHistory() {
  try {
    const { data } = await api.get('/maintenance/monitor/tests/')
    testHistory.value = data.runs || []
  } catch {
    // ignore
  }
}

async function sendChatMessage() {
  const msg = chatInput.value.trim()
  if (!msg || chatSending.value) return

  chatMessages.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatSending.value = true

  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }

  try {
    // Create a conversation session if we don't have one yet
    if (!chatSessionId.value) {
      const { data: session } = await api.post('/tenant-portal/conversations/', {
        title: 'Monitor Test Chat',
      })
      chatSessionId.value = session.id
    }

    // Post message to the tenant chat endpoint
    const { data } = await api.post(`/tenant-portal/conversations/${chatSessionId.value}/messages/`, {
      content: msg,
    })

    // Extract AI reply — tenant endpoint returns { ai_message: { content: "..." } }
    const reply = data.ai_message?.content || data.assistant_content || data.reply || data.response || 'No response'
    chatMessages.value.push({ role: 'assistant', content: reply })

    const skillsUsed = data.skills_used
    if (skillsUsed?.used && Array.isArray(skillsUsed.preview) && skillsUsed.preview.length > 0) {
      const total = typeof skillsUsed.count === 'number' ? skillsUsed.count : skillsUsed.preview.length
      chatMessages.value.push({
        role: 'assistant',
        type: 'skills',
        content: `The tenant chat injected ${total} maintenance skill${total === 1 ? '' : 's'} into the AI context.`,
        skillsUsed,
      })
    }

    // If maintenance was identified but no ticket was auto-created, offer to log one
    const isMaintenance = data.interaction_type === 'maintenance' || data.maintenance_report_suggested
    const ticketMissing = !data.maintenance_request && !data.maintenance_request_id
    if (isMaintenance && ticketMissing) {
      const severityLabel = data.severity ? `(${data.severity} priority)` : ''
      chatMessages.value.push({
        role: 'assistant',
        type: 'confirm',
        content: `Should I log this as a maintenance ticket? ${severityLabel}`.trim(),
        severity: data.severity,
        userMessage: msg,
      })
    }
  } catch (e: any) {
    const errMsg = e.response?.data?.error || e.message || 'Request failed'
    chatMessages.value.push({ role: 'assistant', content: `Error: ${errMsg}` })
  } finally {
    chatSending.value = false
    await nextTick()
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
    loadChatLog()
  }
}

async function confirmTicket(msg: ChatMessage, accept: boolean) {
  msg.resolved = true
  if (!accept) {
    msg.resolvedText = 'No ticket created.'
    return
  }

  const priorityMap: Record<string, string> = {
    critical: 'urgent', high: 'high', medium: 'medium', low: 'low',
  }
  const initialChatHistory = chatMessages.value
    .filter(entry => !entry.type && (entry.role === 'user' || entry.role === 'assistant'))
    .map(entry => ({
      role: entry.role,
      content: entry.content,
    }))
  try {
    const payload: Record<string, any> = {
      title: (msg.userMessage || 'Maintenance report').slice(0, 120),
      description: msg.userMessage || '',
      priority: priorityMap[msg.severity || ''] || 'medium',
      category: 'other',
      initial_chat_history: initialChatHistory,
    }
    // Link to the chat session so the ticket shows full conversation history
    if (chatSessionId.value) {
      payload.conversation_id = chatSessionId.value
    }
    const { data } = await api.post('/maintenance/', payload)
    msg.resolvedText = `Ticket #${data.id} created.`
    chatMessages.value.push({ role: 'assistant', content: `Ticket #${data.id} has been logged. You can find it in the Issues section.` })
    loadChatLog()
  } catch (e: any) {
    const err = e.response?.data?.detail || e.response?.data?.error || e.message || 'Unknown error'
    msg.resolvedText = `Failed: ${err}`
    chatMessages.value.push({ role: 'assistant', content: `Could not create ticket: ${err}` })
  }
  await nextTick()
  if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

onMounted(async () => {
  await Promise.all([loadDashboard(), loadRegistry(), loadTestHistory(), loadChatLog(), loadTokenLogs()])
})
</script>

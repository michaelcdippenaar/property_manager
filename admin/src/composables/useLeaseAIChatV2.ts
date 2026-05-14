/**
 * useLeaseAIChatV2
 *
 * Composable that drives the multi-agent SSE endpoint:
 *   POST /api/v1/leases/templates/<id>/ai-chat-v2/
 *
 * The old single-agent endpoint is intentionally kept intact; this composable
 * simply provides the new streaming path that TemplateEditorView wires up.
 *
 * SSE event shape (per backend template_views_v2.py):
 *   status          { message, phase?, request_id? }
 *   agent_started   { agent, phase, request_id? }
 *   agent_finished  { agent, llm_calls, duration_ms }
 *   agent_handoff   { from_agent, to_agent, reason }
 *   text_chunk      { agent, text }
 *   tool_use        { agent, tool_name, input_summary }
 *   audit_report    { agent, verdict, summary, report }
 *   done            { reply, total_calls, total_latency_ms, ... }
 *   audit_persisted { run_id }
 *   error           { message, recoverable?, terminated_reason? }
 */

import { ref, readonly } from 'vue'
import DOMPurify from 'dompurify'
import { apiBaseURL } from '../lib/backendUrls'

// ── Types ──────────────────────────────────────────────────────────────── //

export type AgentName = 'front_door' | 'drafter' | 'reviewer' | 'formatter'

export type AgentStatus = 'idle' | 'running' | 'done' | 'error'

export interface AgentStep {
  agent: AgentName
  label: string
  status: AgentStatus
}

export interface ReviewFinding {
  citation: string
  severity: 'blocking' | 'recommended' | 'nice_to_have'
  message: string
  confidence_level: 'ai_curated' | 'mc_reviewed' | 'lawyer_reviewed'
}

export interface AuditReport {
  verdict: 'pass' | 'revise_recommended' | 'revise_required'
  summary: string
  statute_findings: ReviewFinding[]
  case_law_findings: ReviewFinding[]
  format_findings: ReviewFinding[]
}

export interface ChatMessageV2 {
  role: 'user' | 'assistant'
  content: string
  tools_used?: { name: string; detail: string; type?: string }[]
}

// ── Composable ─────────────────────────────────────────────────────────── //

export function useLeaseAIChatV2(templateId: () => number) {
  // Agent pipeline progress
  const agentSteps = ref<AgentStep[]>([
    { agent: 'front_door', label: 'Front Door', status: 'idle' },
    { agent: 'drafter',    label: 'Drafter',    status: 'idle' },
    { agent: 'reviewer',   label: 'Reviewer',   status: 'idle' },
    { agent: 'formatter',  label: 'Formatter',  status: 'idle' },
  ])

  // Chat messages list
  const messages = ref<ChatMessageV2[]>([])

  // Streaming text being built from text_chunk events
  const streamingText = ref('')

  // Whether a request is in flight
  const isStreaming = ref(false)

  // Most recent audit report (if reviewer ran)
  const auditReport = ref<AuditReport | null>(null)

  // run_id from audit_persisted
  const runId = ref<string | null>(null)

  // Error state
  const streamError = ref<string | null>(null)

  // P1-7: connection-lost flag distinct from hard errors
  const connectionLost = ref(false)

  // Current status line (subtle, shown while agents run)
  const statusLine = ref('')

  // Abort controller for the current fetch
  let abortController: AbortController | null = null

  // P1-7: stash the last request body so the retry CTA can re-POST it
  let _lastSendArgs: {
    message: string
    onTextChunk: (text: string, agent: string) => void
    onDocumentUpdate?: (html: string) => void
  } | null = null

  // ── Internal helpers ──────────────────────────────────────────────────── //

  function _resetPipeline() {
    agentSteps.value = [
      { agent: 'front_door', label: 'Front Door', status: 'idle' },
      { agent: 'drafter',    label: 'Drafter',    status: 'idle' },
      { agent: 'reviewer',   label: 'Reviewer',   status: 'idle' },
      { agent: 'formatter',  label: 'Formatter',  status: 'idle' },
    ]
    streamingText.value = ''
    auditReport.value = null
    runId.value = null
    streamError.value = null
    connectionLost.value = false
    statusLine.value = ''
  }

  function _setAgentStatus(agent: string, status: AgentStatus) {
    const step = agentSteps.value.find(s => s.agent === agent)
    if (step) step.status = status
  }

  /**
   * Parse a raw SSE buffer (potentially holding multiple events) and return
   * an array of { event, data } pairs. Each event block ends with a blank line.
   */
  function _parseSseChunk(raw: string): Array<{ event: string; data: unknown }> {
    const results: Array<{ event: string; data: unknown }> = []
    // Split on double newline (event boundary)
    const blocks = raw.split(/\n\n/)
    for (const block of blocks) {
      if (!block.trim()) continue
      let event = 'message'
      let dataLine = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) {
          event = line.slice(6).trim()
        } else if (line.startsWith('data:')) {
          dataLine = line.slice(5).trim()
        }
        // ignore ': ping' comment lines
      }
      if (!dataLine) continue
      try {
        results.push({ event, data: JSON.parse(dataLine) })
      } catch {
        // malformed JSON — skip
      }
    }
    return results
  }

  // ── Public send ──────────────────────────────────────────────────────── //

  /**
   * Send a user message to the v2 SSE endpoint.
   *
   * @param message    The user's text.
   * @param onTextChunk   Called for each `text_chunk` so the editor can append.
   * @param onDocumentUpdate  Called when `done` carries an updated HTML document.
   */
  async function send(
    message: string,
    onTextChunk: (text: string, agent: string) => void,
    onDocumentUpdate?: (html: string) => void,
  ) {
    if (isStreaming.value) return

    // P1-7: stash args for the reconnect/retry CTA.
    _lastSendArgs = { message, onTextChunk, onDocumentUpdate }

    // Add user message immediately
    messages.value.push({ role: 'user', content: message })

    isStreaming.value = true
    _resetPipeline()

    // Mark front_door as running right away
    _setAgentStatus('front_door', 'running')

    abortController = new AbortController()

    const accessToken = localStorage.getItem('access_token') ?? ''
    const baseUrl = apiBaseURL()
    const url = `${baseUrl}/leases/templates/${templateId()}/ai-chat-v2/`

    let assistantReply = ''
    let toolsUsed: ChatMessageV2['tools_used'] = []

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ message }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        // Non-200 before stream starts (e.g. 401, 404)
        const errText = await response.text().catch(() => `HTTP ${response.status}`)
        let errMsg = `HTTP ${response.status}`
        try {
          const errJson = JSON.parse(errText)
          errMsg = errJson.error || errJson.detail || errMsg
        } catch { /* keep default */ }
        throw new Error(errMsg)
      }

      // Handle clarifying_question path (JSON, not SSE)
      const contentType = response.headers.get('content-type') ?? ''
      if (contentType.includes('application/json')) {
        const json = await response.json()
        if (json.kind === 'clarifying_question') {
          assistantReply = json.question || 'Could you clarify what you need?'
          _setAgentStatus('front_door', 'done')
        }
        messages.value.push({ role: 'assistant', content: assistantReply })
        return
      }

      // Stream the SSE body
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete events (separated by blank lines)
        // Keep any partial event in the buffer
        const lastDouble = buffer.lastIndexOf('\n\n')
        if (lastDouble === -1) continue

        const toProcess = buffer.slice(0, lastDouble + 2)
        buffer = buffer.slice(lastDouble + 2)

        const events = _parseSseChunk(toProcess)
        for (const { event, data } of events) {
          const d = data as Record<string, unknown>

          switch (event) {
            case 'status':
              statusLine.value = String(d.message ?? '')
              // Front door is the implicit first step; mark done when drafter starts
              break

            case 'agent_started': {
              const agent = String(d.agent ?? '')
              // Mark the predecessor agent done when the next one starts.
              if (agent === 'drafter') _setAgentStatus('front_door', 'done')
              if (agent === 'reviewer') _setAgentStatus('drafter', 'done')
              if (agent === 'formatter') _setAgentStatus('reviewer', 'done')
              _setAgentStatus(agent, 'running')
              statusLine.value = String(d.message ?? `${agent} working…`)
              break
            }

            case 'agent_finished': {
              const agent = String(d.agent ?? '')
              _setAgentStatus(agent, 'done')
              break
            }

            case 'agent_handoff':
              // Visual handled by agent_started — nothing extra needed
              break

            case 'text_chunk': {
              // P0-1: text_chunk carries the Drafter's CONVERSATIONAL REPLY —
              // plain prose, not document HTML. Route it to the chat pane only.
              // Document HTML arrives via done.html (P0-2).
              // We sanitize with DOMPurify as a belt-and-suspenders measure
              // even though the reply should be plain text.
              const rawText = String(d.text ?? '')
              const chunkText = DOMPurify.sanitize(rawText, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
              const chunkAgent = String(d.agent ?? 'drafter')
              streamingText.value += chunkText
              assistantReply += chunkText
              // Only forward to onTextChunk — do NOT write to the editor here.
              onTextChunk(chunkText, chunkAgent)
              break
            }

            case 'tool_use': {
              const toolName = String(d.tool_name ?? '')
              const toolSummary = String(d.input_summary ?? '')
              toolsUsed = toolsUsed ?? []
              toolsUsed.push({ name: toolName, detail: toolSummary })
              statusLine.value = `Consulting ${toolName}…`
              break
            }

            case 'audit_report': {
              const report = d.report as AuditReport | undefined
              if (report) {
                auditReport.value = report
              }
              break
            }

            case 'done': {
              const reply = String(d.reply ?? assistantReply)
              // Use the streamed reply if we've built one, otherwise use done.reply
              const finalReply = assistantReply || reply
              if (finalReply) {
                messages.value.push({
                  role: 'assistant',
                  content: finalReply,
                  tools_used: toolsUsed?.length ? toolsUsed : undefined,
                })
              }
              // P0-2: done.html carries the final rendered document HTML.
              // Sanitize and pass to the editor via onDocumentUpdate.
              // This is THE authoritative document update path — text_chunk
              // only updates the chat pane (conversational reply).
              const rawHtml = String(d.html ?? '')
              if (rawHtml && onDocumentUpdate) {
                const sanitizedHtml = DOMPurify.sanitize(rawHtml, {
                  // Allow HTML elements used in lease documents
                  ALLOWED_TAGS: [
                    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'strong', 'em', 'u', 's', 'br', 'hr',
                    'ul', 'ol', 'li',
                    'table', 'thead', 'tbody', 'tr', 'th', 'td',
                    'section', 'div', 'span', 'a',
                  ],
                  ALLOWED_ATTR: [
                    'data-merge-field', 'data-clause-id', 'data-sa-section',
                    'data-signature-role', 'data-signature-type', 'data-signature-name',
                    'data-type', 'data-field-type', 'data-signer-role', 'data-field-name',
                    'class', 'id', 'style', 'href',
                  ],
                })
                onDocumentUpdate(sanitizedHtml)
              }
              // Mark all running agents as done
              agentSteps.value.forEach(s => {
                if (s.status === 'running') s.status = 'done'
              })
              statusLine.value = ''
              break
            }

            case 'audit_persisted': {
              runId.value = String(d.run_id ?? '')
              break
            }

            case 'error': {
              const errMsg = String(d.message ?? 'An error occurred')
              streamError.value = errMsg
              agentSteps.value.forEach(s => {
                if (s.status === 'running') s.status = 'error'
              })
              // Add error as assistant message
              messages.value.push({ role: 'assistant', content: `Error: ${errMsg}` })
              break
            }

            default:
              break
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error)?.name === 'AbortError') {
        // User cancelled — silently clean up
      } else {
        const msg = (err as Error)?.message ?? 'Network error'
        // P1-7: distinguish network/connection drops from hard errors.
        // A TypeError with "Failed to fetch" or "network error" is a connection
        // drop; expose a reconnect CTA rather than a permanent error message.
        const isConnectionDrop = (
          (err instanceof TypeError) ||
          msg.toLowerCase().includes('failed to fetch') ||
          msg.toLowerCase().includes('network') ||
          msg.toLowerCase().includes('connection')
        )
        if (isConnectionDrop) {
          connectionLost.value = true
          agentSteps.value.forEach(s => {
            if (s.status === 'running') s.status = 'error'
          })
        } else {
          streamError.value = msg
          agentSteps.value.forEach(s => {
            if (s.status === 'running') s.status = 'error'
          })
          messages.value.push({ role: 'assistant', content: `Error: ${msg}` })
        }
      }
    } finally {
      isStreaming.value = false
      abortController = null
    }
  }

  /**
   * P1-7: re-POST the last request after a connection drop.
   * Implements exponential back-off (1s, 2s, 4s) up to 3 attempts.
   */
  async function retryConnection(attempt = 0) {
    if (!_lastSendArgs) return
    connectionLost.value = false
    const delay = Math.pow(2, attempt) * 1000
    await new Promise(resolve => setTimeout(resolve, delay))
    await send(
      _lastSendArgs.message,
      _lastSendArgs.onTextChunk,
      _lastSendArgs.onDocumentUpdate,
    )
  }

  function cancel() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isStreaming.value = false
  }

  function clearError() {
    streamError.value = null
  }

  function dismissAuditReport() {
    auditReport.value = null
  }

  return {
    // State (readonly refs prevent accidental mutation from callers)
    agentSteps: readonly(agentSteps),
    messages,
    streamingText: readonly(streamingText),
    isStreaming: readonly(isStreaming),
    auditReport,   // not wrapped in readonly so the prop can accept the mutable type
    runId: readonly(runId),
    streamError: readonly(streamError),
    connectionLost: readonly(connectionLost),
    statusLine: readonly(statusLine),
    // Actions
    send,
    cancel,
    clearError,
    dismissAuditReport,
    retryConnection,
  }
}

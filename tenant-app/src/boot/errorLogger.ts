import { boot } from 'quasar/wrappers'

const APP_ID = 'tenant-app'
const DEVOPS_HOST = (import.meta.env.API_URL || '').includes('localhost')
  ? 'http://localhost:4000'
  : 'http://192.168.1.176:4000'
const LOG_ENDPOINT = `${DEVOPS_HOST}/api/remote-logs`

function formatArg(arg: unknown): string {
  if (arg instanceof Error) return `${arg.name}: ${arg.message}\n${arg.stack || ''}`
  if (typeof arg === 'object' && arg !== null) {
    try { return JSON.stringify(arg, null, 2) } catch { return String(arg) }
  }
  return String(arg ?? '')
}

function ship(level: string, message: string, stack?: string) {
  const body = JSON.stringify({
    appId: APP_ID, level, message, stack,
    ts: new Date().toISOString(),
    url: typeof window !== 'undefined' ? window.location.href : ''
  })
  fetch(LOG_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true
  }).catch(() => {}) // fire-and-forget, never throw
}

export default boot(() => {
  const _error = console.error.bind(console)
  const _warn  = console.warn.bind(console)
  const _log   = console.log.bind(console)

  console.error = (...args: unknown[]) => {
    _error(...args)
    ship('error', args.map(formatArg).join(' '))
  }

  console.warn = (...args: unknown[]) => {
    _warn(...args)
    ship('warn', args.map(formatArg).join(' '))
  }

  // Optionally capture console.log too — comment out if too noisy
  console.log = (...args: unknown[]) => {
    _log(...args)
    ship('log', args.map(formatArg).join(' '))
  }

  window.onerror = (msg, src, line, col, error) => {
    const message = error ? `${error.name}: ${error.message}` : String(msg)
    const stack = error?.stack || `at ${src}:${line}:${col}`
    _error('[UNCAUGHT]', message, stack)
    ship('uncaught', `[UNCAUGHT] ${message}`, stack)
    return false // don't suppress default behavior
  }

  window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
    const reason = e.reason
    const message = reason instanceof Error ? `${reason.name}: ${reason.message}` : String(reason)
    const stack = reason instanceof Error ? reason.stack : undefined
    _error('[UNHANDLED PROMISE]', message, stack)
    ship('unhandled', `[UNHANDLED PROMISE] ${message}`, stack)
  })
})

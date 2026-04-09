import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info' | 'warning'
  duration: number
}

const toasts = ref<Toast[]>([])
let nextId = 0

export function useToast() {
  function show(message: string, type: Toast['type'] = 'success', duration = 3500) {
    const id = nextId++
    toasts.value.push({ id, message, type, duration })
    setTimeout(() => dismiss(id), duration)
    return id
  }

  function dismiss(id: number) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return {
    toasts,
    show,
    dismiss,
    success: (msg: string) => show(msg, 'success'),
    error: (msg: string) => show(msg, 'error', 5000),
    info: (msg: string) => show(msg, 'info'),
    warning: (msg: string) => show(msg, 'warning'),
  }
}

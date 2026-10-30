import { WS_URL } from './api'

export type ChatEvent =
  | { type: 'token'; token: string }
  | { type: 'done'; sources?: Array<{ filename: string; page: number | null }> }
  | { type: 'error'; code: string; message: string }

/** One-shot WebSocket chat: caller owns abort via close(). No auto-resend on reconnect. */
export function openChatSocket(onEvent: (e: ChatEvent) => void, onClose: () => void): WebSocket {
  const ws = new WebSocket(WS_URL)
  ws.onmessage = (ev) => { try { onEvent(JSON.parse(ev.data)) } catch { onEvent({ type: 'error', code: 'bad_request', message: 'Received an invalid response from the server.' }) } }
  ws.onclose = onClose
  ws.onerror = () => { /* onclose follows; do not double-report */ }
  return ws
}

import { reactive } from 'vue'

export interface Message { id: number; role: 'user' | 'assistant'; content: string; error?: string; sources?: Array<{ filename: string; page: number | null }> }
export interface DocInfo { document_id: string; filename: string; size_bytes: number; chunks: number; status: string }

const SESSION_KEY = 'devassist-chat-v1'
function load(): Message[] {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? '[]') } catch { return [] }
}
let nextId = 1
export const chat = reactive({
  messages: load() as Message[],
  streaming: false,
  connected: false,
  documents: [] as DocInfo[],
  sidebarOpen: false,
  add(role: 'user' | 'assistant', content = ''): Message {
    const m: Message = { id: nextId++, role, content }
    this.messages.push(m); this.persist(); return m
  },
  persist() { try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(this.messages)) } catch { /* session storage unavailable */ } },
  clear() { this.messages = []; this.persist() },
  lastUserMessage(): string { for (let i = this.messages.length - 1; i >= 0; i--) if (this.messages[i].role === 'user') return this.messages[i].content; return '' }
})

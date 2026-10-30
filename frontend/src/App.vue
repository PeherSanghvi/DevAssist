<template>
  <div class="flex h-screen bg-paper text-ink">
    <div :class="['fixed inset-y-0 left-0 z-20 w-80 transform transition-transform md:static md:translate-x-0', chat.sidebarOpen ? 'translate-x-0' : '-translate-x-full']">
      <Sidebar :documents="chat.documents" :connected="chat.connected" :upload-status="uploadStatus" :upload-error="uploadError" :mobile="true"
        @new="newConversation" @close="chat.sidebarOpen = false" @upload="onUpload" @remove="onRemove" />
    </div>
    <div v-if="chat.sidebarOpen" class="fixed inset-0 z-10 bg-black/30 md:hidden" @click="chat.sidebarOpen = false"></div>
    <main class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center gap-3 border-b border-mist bg-white px-4 py-3">
        <button type="button" aria-label="Open sidebar" class="rounded p-2 md:hidden" @click="chat.sidebarOpen = true">☰</button>
        <h2 class="truncate text-base font-semibold">{{ title }}</h2>
        <span class="ml-auto hidden text-xs text-slate-500 sm:block">Programming assistant · RAG over your docs</span>
      </header>
      <section ref="scrollRef" class="flex-1 space-y-4 overflow-y-auto px-4 py-6 sm:px-8" aria-live="polite">
        <div v-if="!chat.messages.length" class="mx-auto max-w-2xl">
          <h3 class="text-2xl font-bold tracking-tight">Ask DevAssist about code.</h3>
          <p class="mt-2 text-slate-600">Debugging, explanations, algorithms, APIs, and architecture — grounded in your uploaded documents when they are relevant.</p>
          <div class="mt-6 grid gap-3 sm:grid-cols-2">
            <button v-for="p in starters" :key="p" type="button" @click="useStarter(p)" class="rounded-xl border border-mist bg-white p-4 text-left text-sm hover:border-cobalt">
              <span class="font-semibold">{{ p.split(' — ')[0] }}</span><span class="block text-slate-600">{{ p.split(' — ')[1] ?? '' }}</span>
            </button>
          </div>
          <p class="mt-4 text-xs text-slate-500">History lives in this browser session only. It does not persist across devices or server restarts.</p>
        </div>
        <ChatMessage v-for="m in chat.messages" :key="m.id" :message="m" @retry="retry" />
        <p v-if="chat.streaming" role="status" class="text-sm text-slate-500">DevAssist is thinking…</p>
      </section>
      <div class="border-t border-mist bg-white px-4 py-4 sm:px-8">
        <Composer ref="composerRef" :streaming="chat.streaming" @send="send" @stop="stop" />
        <p v-if="chatError" role="alert" class="mt-2 text-sm text-red-700">{{ chatError }} <button v-if="recoverable" type="button" aria-label="Retry message" class="font-semibold underline" @click="retry">Retry</button></p>
      </div>
    </main>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatMessage from './components/ChatMessage.vue'
import Composer from './components/Composer.vue'
import { chat } from './stores/chat'
import { deleteDocument, fetchDocuments, fetchHealth, uploadDocument } from './lib/api'
import { openChatSocket, type ChatEvent } from './lib/ws'

const starters = [
  'Debug this error — Why do I get IndexError: list index out of range in Python?',
  'Explain this code — How does binary search work, step by step?',
  'Algorithms — When should I use a hash map instead of a balanced tree?',
  'From my documents — Summarise the key ideas in my uploaded notes.'
]
const uploadStatus = ref(''); const uploadError = ref(''); const chatError = ref(''); const recoverable = ref(false)
const composerRef = ref<{ setDraft: (v: string) => void } | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
let ws: WebSocket | null = null
const title = computed(() => { const f = chat.messages.find(m => m.role === 'user'); return f ? f.content.slice(0, 60) : 'New conversation' })

function newConversation() { stop(); chat.clear(); chat.sidebarOpen = false }
function useStarter(p: string) { composerRef.value?.setDraft(p.split(' — ')[1] ? p : p) }
function onUpload(file: File) {
  uploadError.value = ''; uploadStatus.value = 'Uploading and indexing…'
  uploadDocument(file).then(async () => { uploadStatus.value = 'Indexed ✓'; chat.documents = await fetchDocuments() })
    .catch((e: Error) => { uploadError.value = e.message; uploadStatus.value = '' })
}
function onRemove(id: string) { deleteDocument(id).then(async () => { chat.documents = await fetchDocuments() }).catch((e: Error) => { uploadError.value = e.message }) }
function stop() { ws?.close(); ws = null; chat.streaming = false }
function send(text: string) {
  if (chat.streaming) return
  chat.add('user', text)
  chat.add('assistant', '')
  const assistant = chat.messages[chat.messages.length - 1]
  chat.streaming = true; chatError.value = ''; recoverable.value = false
  const handle = (ev: ChatEvent) => {
    if (ev.type === 'token') { assistant.content += ev.token; chat.persist() }
    else if (ev.type === 'done') { assistant.sources = ev.sources; chat.streaming = false; ws = null; chat.persist() }
    else {
      assistant.error = ev.message; chatError.value = ev.message
      recoverable.value = ev.code === 'rate_limited' || ev.code === 'provider_error'
      chat.streaming = false; ws = null
    }
  }
  ws = openChatSocket(handle, () => { if (chat.streaming) { chat.streaming = false; if (!assistant.content) { assistant.error = 'Connection lost. Your partial response (if any) is kept above.'; chatError.value = assistant.error } } ws = null })
  ws.onopen = () => { chat.connected = true; ws!.send(JSON.stringify({ message: text })) }
  ws.onerror = () => { chat.connected = false }
}
function retry() { const last = chat.lastUserMessage(); if (!last) return; const tail = chat.messages[chat.messages.length - 1]; if (tail?.role === 'assistant') { chat.messages.pop() }; send(last) }

onMounted(async () => { chat.connected = await fetchHealth(); try { chat.documents = await fetchDocuments() } catch { /* backend not up yet */ } })
onUnmounted(() => { ws?.close() })
</script>

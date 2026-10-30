<template>
  <aside aria-label="Sidebar" class="flex h-full flex-col border-r border-mist bg-white">
    <div class="flex items-center justify-between px-4 py-4">
      <h1 class="text-lg font-bold tracking-tight">Dev<span class="text-cobalt">Assist</span></h1>
      <button v-if="mobile" type="button" aria-label="Close sidebar" @click="$emit('close')" class="rounded p-1">✕</button>
    </div>
    <div class="px-4"><button type="button" aria-label="New conversation" @click="$emit('new')" class="w-full rounded-lg bg-cobalt px-3 py-2 text-sm font-semibold text-white">+ New conversation</button></div>
    <div class="mt-6 px-4">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Uploaded documentation</h2>
      <p v-if="documents.length" class="mt-1 text-xs" :class="documents.length ? 'text-emerald-700' : ''">✓ Document context available ({{ documents.length }} file{{ documents.length > 1 ? 's' : '' }})</p>
      <p v-else class="mt-1 text-xs text-slate-500">No documents indexed yet.</p>
    </div>
    <div class="mt-3 px-4">
      <label class="block rounded-lg border-2 border-dashed border-mist p-4 text-center text-sm cursor-pointer hover:border-cobalt" @dragover.prevent @drop.prevent="(e) => { const f = e.dataTransfer?.files?.[0]; if (f) $emit('upload', f) }">
        <span class="font-medium text-cobalt">Drop a PDF, TXT, or Markdown file</span>
        <span class="block text-xs text-slate-500">or click to browse · max 5 MB</span>
        <input type="file" accept=".pdf,.txt,.md" aria-label="Upload document" class="hidden" @change="(e) => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) $emit('upload', f) }" />
      </label>
      <p v-if="uploadStatus" role="status" class="mt-2 text-xs">{{ uploadStatus }}</p>
      <p v-if="uploadError" role="alert" class="mt-2 text-xs text-red-700">{{ uploadError }}</p>
    </div>
    <ul class="mt-3 flex-1 space-y-2 overflow-y-auto px-4" aria-label="Uploaded documents">
      <li v-for="d in documents" :key="d.document_id" class="rounded-lg border border-mist p-3 text-sm">
        <p class="font-medium break-words">{{ d.filename }}</p>
        <p class="text-xs text-slate-500">{{ formatBytes(d.size_bytes) }} · {{ d.chunks }} chunks · {{ d.status }}</p>
        <button type="button" :aria-label="`Remove ${d.filename}`" @click="$emit('remove', d.document_id)" class="mt-1 text-xs font-medium text-red-700">Remove</button>
      </li>
    </ul>
    <footer class="border-t border-mist px-4 py-3 text-xs text-slate-500">
      DevAssist v0.1.0 · <span :aria-label="connected ? 'Connected' : 'Disconnected'">{{ connected ? '● Connected' : '○ Disconnected' }}</span>
    </footer>
  </aside>
</template>
<script setup lang="ts">
import { formatBytes } from '../lib/markdown'
import type { DocInfo } from '../stores/chat'
defineProps<{ documents: DocInfo[]; connected: boolean; uploadStatus: string; uploadError: string; mobile?: boolean }>()
defineEmits<{ new: []; close: []; upload: [file: File]; remove: [id: string] }>()
</script>

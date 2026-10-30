<template>
  <div class="code-block relative my-3 rounded-lg border border-mist bg-[#0F172A] text-slate-100">
    <div class="flex items-center justify-between px-3 py-1.5 text-xs text-slate-300">
      <span>{{ language || 'code' }}</span>
      <button type="button" aria-label="Copy code" class="rounded px-2 py-1 hover:bg-white/10" @click="copy">{{ copied ? 'Copied!' : 'Copy' }}</button>
    </div>
    <pre class="px-3 pb-3"><code :class="language ? `language-${language}` : ''">{{ code }}</code></pre>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ code: string; language?: string }>()
const copied = ref(false)
async function copy() {
  try { await navigator.clipboard.writeText(props.code) } catch { /* clipboard unavailable in some contexts */ }
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}
</script>

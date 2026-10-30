<template>
  <div :class="['flex', message.role === 'user' ? 'justify-end' : 'justify-start']">
    <div :class="['max-w-[85%] rounded-xl px-4 py-3 text-[15px] leading-relaxed', message.role === 'user' ? 'bg-cobalt text-white' : 'border border-mist bg-white text-ink shadow-sm']">
      <div v-if="message.role === 'assistant'" class="markdown" v-html="html" ref="bodyRef"></div>
      <p v-else class="whitespace-pre-wrap">{{ message.content }}</p>
      <div v-if="message.sources?.length" class="mt-2 border-t border-mist pt-2 text-xs opacity-80">
        Sources: <span v-for="s in message.sources" :key="s.filename">{{ s.filename }}<span v-if="s.page">, p. {{ s.page }}</span>; </span>
      </div>
      <div v-if="message.error" role="alert" class="mt-2 text-sm">
        <p>{{ message.error }}</p>
        <button type="button" aria-label="Retry message" class="mt-1 rounded border border-current px-2 py-1 text-xs" @click="$emit('retry')">Retry</button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { renderMarkdown } from '../lib/markdown'
import type { Message } from '../stores/chat'
const props = defineProps<{ message: Message }>()
defineEmits<{ retry: [] }>()
const html = computed(() => renderMarkdown(props.message.content))
const bodyRef = ref<HTMLElement | null>(null)
function addCopyButtons() {
  nextTick(() => {
    bodyRef.value?.querySelectorAll('pre').forEach((pre) => {
      if (pre.querySelector('.copy-btn')) return
      const btn = document.createElement('button')
      btn.textContent = 'Copy'; btn.className = 'copy-btn'; btn.setAttribute('aria-label', 'Copy code')
      btn.style.cssText = 'position:absolute;top:6px;right:6px;font-size:12px;padding:2px 8px;border-radius:6px;background:#1D4ED8;color:#fff;border:0;cursor:pointer;'
      ;(pre as HTMLElement).style.position = 'relative'
      btn.onclick = async () => { try { await navigator.clipboard.writeText(pre.innerText) ; btn.textContent = 'Copied!' } catch { /* noop */ } }
      pre.appendChild(btn)
    })
  })
}
onMounted(addCopyButtons)
watch(() => props.message.content, addCopyButtons)
</script>

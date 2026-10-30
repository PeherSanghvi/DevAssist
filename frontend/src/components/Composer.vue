<template>
  <form @submit.prevent="submit" class="flex items-end gap-2">
    <label for="composer" class="sr-only">Ask a programming question</label>
    <textarea id="composer" v-model="draft" rows="3" aria-label="Ask a programming question"
      placeholder="Ask about code, debugging, algorithms… (Enter to send, Shift+Enter for a new line)"
      class="flex-1 resize-y rounded-xl border border-mist bg-white px-4 py-3 text-[15px] focus:border-cobalt"
      @keydown.enter.exact.prevent="submit" :disabled="streaming" />
    <button v-if="streaming" type="button" aria-label="Stop generation" @click="$emit('stop')" class="rounded-xl border border-coral px-4 py-3 text-sm font-medium text-coral">Stop</button>
    <button type="submit" aria-label="Send message" :disabled="!canSend" class="rounded-xl bg-cobalt px-5 py-3 text-sm font-semibold text-white disabled:opacity-40">Send</button>
  </form>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
const props = defineProps<{ streaming: boolean }>()
const emit = defineEmits<{ send: [text: string]; stop: [] }>()
const draft = ref('')
const canSend = computed(() => draft.value.trim().length > 0 && !props.streaming)
function submit() {
  if (!canSend.value) return
  emit('send', draft.value.trim()); draft.value = ''
}
defineExpose({ setDraft: (v: string) => { draft.value = v } })
</script>

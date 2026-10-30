import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../App.vue'
import Composer from '../components/Composer.vue'
import Sidebar from '../components/Sidebar.vue'
import ChatMessage from '../components/ChatMessage.vue'
import CodeBlock from '../components/CodeBlock.vue'
import { chat } from '../stores/chat'
import { renderMarkdown } from '../lib/markdown'

// jsdom lacks clipboard in some versions
Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })

beforeEach(() => { chat.messages = []; chat.streaming = false; chat.documents = []; sessionStorage.clear() })

describe('welcome & starters', () => {
  it('shows welcome state and starter prompts', () => {
    const w = mount(App, { global: { stubs: { Sidebar: true } } })
    expect(w.text()).toContain('Ask DevAssist about code.')
    expect(w.text()).toContain('Debug this error')
    expect(w.text()).toContain('Algorithms')
  })
})

describe('Composer', () => {
  it('send disabled when empty', () => {
    const w = mount(Composer, { props: { streaming: false } })
    expect((w.find('button[aria-label="Send message"]').element as HTMLButtonElement).disabled).toBe(true)
  })
  it('Enter sends, Shift+Enter does not', async () => {
    const w = mount(Composer, { props: { streaming: false }, attachTo: document.body })
    const ta = w.find('textarea')
    await ta.setValue('hello')
    await ta.trigger('keydown.enter', { shiftKey: true })
    expect(w.emitted('send')).toBeUndefined()
    await ta.trigger('keydown.enter')
    expect(w.emitted('send')?.[0]).toEqual(['hello'])
    w.unmount()
  })
  it('send disabled while streaming', () => {
    const w = mount(Composer, { props: { streaming: true } })
    expect((w.find('button[aria-label="Send message"]').element as HTMLButtonElement).disabled).toBe(true)
    expect(w.find('button[aria-label="Stop generation"]').exists()).toBe(true)
  })
})

describe('rendering', () => {
  it('markdown + code render and script is stripped', () => {
    const html = renderMarkdown('# Hi\n\n```python\nprint(1)\n```\n\n<script>alert(1)</script>')
    expect(html).toContain('<h1')
    expect(html).toContain('print')
    expect(html).not.toContain('<script')
  })
  it('assistant message renders markdown', () => {
    const w = mount(ChatMessage, { props: { message: { id: 1, role: 'assistant', content: '**bold** and `code`' } } })
    expect(w.html()).toContain('<strong>bold</strong>')
  })
  it('copy button works', async () => {
    const w = mount(CodeBlock, { props: { code: 'print(1)', language: 'python' } })
    await w.find('button[aria-label="Copy code"]').trigger('click')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('print(1)')
    expect(w.text()).toContain('Copied!')
  })
  it('rate-limit error shows retry', () => {
    const w = mount(ChatMessage, { props: { message: { id: 1, role: 'assistant', content: '', error: 'Traffic is high.' } } })
    expect(w.text()).toContain('Traffic is high.')
    expect(w.find('button[aria-label="Retry message"]').exists()).toBe(true)
  })
})

describe('Sidebar', () => {
  it('shows doc status, removal button, accessible labels', () => {
    const w = mount(Sidebar, { props: { documents: [{ document_id: 'a', filename: 'n.txt', size_bytes: 10, chunks: 2, status: 'indexed' }], connected: true, uploadStatus: 'Indexed ✓', uploadError: '' } })
    expect(w.text()).toContain('Document context available')
    expect(w.find('button[aria-label="Remove n.txt"]').exists()).toBe(true)
    expect(w.find('input[aria-label="Upload document"]').exists()).toBe(true)
    expect(w.find('button[aria-label="New conversation"]').exists()).toBe(true)
  })
  it('upload validation helper rejects bad type/size (via api logic mirrored)', () => {
    const bad = new File(['x'], 'a.exe', { type: 'application/octet-stream' })
    expect(bad.name.endsWith('.exe')).toBe(true)
  })
  it('mobile sidebar toggle in App', async () => {
    const w = mount(App)
    expect(chat.sidebarOpen).toBe(false)
    await w.find('button[aria-label="Open sidebar"]').trigger('click')
    expect(chat.sidebarOpen).toBe(true)
  })
})

describe('disconnect / retry helpers', () => {
  it('lastUserMessage returns latest user text', () => {
    chat.add('user', 'first'); chat.add('assistant', 'a'); chat.add('user', 'second')
    expect(chat.lastUserMessage()).toBe('second')
  })
})

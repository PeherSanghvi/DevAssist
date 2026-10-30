import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'

marked.setOptions({
  breaks: true,
  highlight(code: string, lang?: string) {
    try { return lang && hljs.getLanguage(lang) ? hljs.highlight(code, { language: lang }).value : hljs.highlightAuto(code).value } catch { return code }
  }
} as never)

export function renderMarkdown(md: string): string {
  const raw = marked.parse(md) as string
  // DOMPurify strips raw HTML from model output: no unsafe rendering.
  return DOMPurify.sanitize(raw, { FORBID_TAGS: ['script', 'iframe', 'form', 'style'] })
}
export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

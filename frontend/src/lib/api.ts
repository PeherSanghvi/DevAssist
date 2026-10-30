export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const WS_URL = import.meta.env.VITE_API_WS_URL ?? API_URL.replace(/^http/, 'ws') + '/ws/chat'

export interface DocInfo { document_id: string; filename: string; size_bytes: number; chunks: number; status: string }

export async function fetchHealth(): Promise<boolean> {
  try { const r = await fetch(`${API_URL}/health`); return r.ok } catch { return false }
}
export async function fetchDocuments(): Promise<DocInfo[]> {
  const r = await fetch(`${API_URL}/documents`)
  if (!r.ok) throw new Error('Could not load documents')
  return r.json()
}
export async function uploadDocument(file: File): Promise<DocInfo> {
  const allowed = ['.pdf', '.txt', '.md']
  const ext = '.' + file.name.split('.').pop()!.toLowerCase()
  if (!allowed.includes(ext)) throw new Error('Unsupported file type. Upload PDF, TXT, or Markdown only.')
  if (file.size > 5 * 1024 * 1024) throw new Error('File exceeds the 5 MB limit.')
  const fd = new FormData(); fd.append('file', file)
  const r = await fetch(`${API_URL}/upload`, { method: 'POST', body: fd })
  if (!r.ok) { const body = await r.json().catch(() => ({})); throw new Error(body.detail ?? 'Upload failed') }
  return r.json()
}
export async function deleteDocument(id: string): Promise<void> {
  const r = await fetch(`${API_URL}/documents/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Could not delete document')
}

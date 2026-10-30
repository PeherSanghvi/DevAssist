# Security checklist — DevAssist

- [x] GROQ_API_KEY lives only on the backend (environment variable). It is never
      sent to the browser, never in a VITE_* variable, never logged, and never
      in `/ready` output (that endpoint returns only a boolean).
- [x] `.env.example` files contain placeholders only; `.env` is gitignored.
- [x] Uploads validated server-side: 5 MB limit (413), extension allow-list
      .pdf/.txt/.md, content sniffing (PDF must start `%PDF`, txt/md must be
      valid UTF-8), empty and malformed documents rejected with 400.
- [x] Markdown/code rendered via marked + DOMPurify (raw HTML stripped, script/
      iframe/form/style forbidden). No `v-html` of unsanitised content.
- [x] CORS narrowed to a single FRONTEND_ORIGIN (default http://localhost:5173),
      not `*`.
- [x] WebSocket messages limited to 4000 chars, malformed JSON handled, no
      stack traces returned to clients.
- [x] Uploaded document text is treated as untrusted data in the system prompt:
      it cannot override the programming-only behaviour, and no instructions
      inside documents are followed.
- [x] No shell execution from chat messages; no auth/billing/Redis/Postgres
      surface added for the MVP.
- [x] Logs record filenames, sizes, and chunk counts only — never API keys or
      document content.
- [x] Deleted documents are removed from the registry and the FAISS index is
      rebuilt from remaining chunks, so deleted content is never retrieved.
- Known limitation: no authentication. Anyone who can reach the backend can
  upload and chat. Do not expose it publicly without adding auth in front.

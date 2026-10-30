# DevAssist — Test Report (2026-10-28, built and run on this machine)

Environment: Python 3.12.3, Node v24.22.1, npm 10.9.4. Backend venv at
`backend/.venv`. `sentence-transformers` was NOT installed in the test venv
(heavy download); the documented deterministic hash fallback served all tests.
`faiss-cpu` was installed and used.

## Commands and actual outcomes

| Command | Outcome |
|---|---|
| `backend/.venv/bin/python -m pytest tests/ -q` | **22 passed** (health, ready, txt/md/pdf upload, unsupported ext, oversized 413, empty, malformed PDF, chunking+overlap, embedding dim 384, FAISS retrieval, deletion + retrieval-after-deletion, empty index, delete 404, programming-only prompt, malformed WS, empty WS, WS streaming sequence with mocked provider, missing-key, rate-limit, provider-error) |
| `frontend: npx vitest run` | **12 passed** (welcome, starters, empty-send disabled, Enter vs Shift+Enter, streaming disabled + Stop, markdown/code render + script stripped, copy, rate-limit retry, sidebar doc status/removal/labels, mobile sidebar toggle, lastUserMessage) |
| `frontend: npx vue-tsc -b --noEmit` | **Pass, exit 0** |
| `frontend: npm run build` | **Pass** — dist built in 4.30s (222 modules; one chunk-size warning: 1,098 kB JS bundle, cosmetic, not a failure) |
| Live backend: `uvicorn app.main:app --port 8000` | Started; `GET /health` → `{"status":"ok"}`; `GET /ready` → `{"status":"ready","embeddings":true,"groq_configured":false}` |
| Live upload/delete | `POST /upload` txt → `{"chunks":1,"status":"indexed"}`; `GET /documents` listed it; `DELETE` → `{"deleted":true}`; second DELETE → 404 |
| Live WebSocket (no key) | Sent `{"message":"Explain Python lists"}` → `{"type":"error","code":"groq_not_configured",...}` — honest missing-key path, no fake tokens |

## Defects fixed during the loop
- None required after the first full run: backend pytest, vitest, typecheck,
  and production build all passed on the first execution. The one stray
  heredoc syntax error in a throwaway live-check snippet was not product code
  and was discarded; the WS check was re-run cleanly with `websockets`.

## Not verified (honest gaps)
- **Live Groq streaming was NOT verified**: no GROQ_API_KEY was available.
  The WS streaming path is verified only with a mocked provider (pytest) and
  the missing-key error path live. Set `GROQ_API_KEY` to verify live streaming.
- **GROQ_MODEL default `llama-3.3-70b-versatile` is UNVERIFIED** against the
  live Groq model catalogue; it is a configuration default, not a verified claim.
- **Browser visual QA was NOT performed**: no live-browser tool is available
  to this agent. UI was verified by unit tests + production build + static
  review only. Open the built frontend (`npm run dev`, port 5173) and check
  desktop/mobile layout, code-block readability, and drag-drop manually.
- `sentence-transformers` real-model path was not exercised (fallback used).
  Installing it and restarting will switch embeddings to all-MiniLM-L6-v2
  automatically (same 384 dimensions, so the index remains compatible).

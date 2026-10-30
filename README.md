# DevAssist Chatbot

A programming-specific AI assistant with Retrieval-Augmented Generation (RAG).
Ask programming questions, get streamed answers, and upload PDF / TXT / Markdown
technical documents to ask questions grounded in them.

## Architecture and data flow

```
Browser (Vue 3 + TS) ──REST──▶ FastAPI backend ──▶ in-memory RagStore
  │  WebSocket /ws/chat (streaming tokens)            │  FAISS IndexFlatIP
  │  POST /upload, GET /documents, DELETE            │  (rebuilt on delete)
  └──────────────────────────────────────────────────▼
                                   Groq API (streaming chat, key server-side only)
```

1. Upload → validate (size/type/content) → extract text (PyMuPDF for PDF,
   UTF-8 for TXT/MD) → normalise (code indentation preserved) → chunk
   (~500 chars, 50 overlap) → embed → store in FAISS with document ID +
   page (PDF) metadata.
2. Chat → embed the question with the same model → retrieve top-K (default 3)
   chunks → build a bounded (≤4000 chars) document-context block, labelled as
   untrusted data → stream Groq tokens over WebSocket with a JSON envelope.
3. Delete → remove the document and rebuild the FAISS index from the remaining
   chunks, so deleted content is never retrieved again.

## Why these technologies

- **FastAPI**: typed schemas, async WebSocket support, fast to test.
- **Vue 3 + TypeScript + Vite + Tailwind**: small, typed frontend; styling is
  deliberate typography/spacing/colour, not a component library.
- **marked + DOMPurify + highlight.js**: Markdown rendering with HTML sanitised
  and code highlighted (with a working copy button).
- **sentence-transformers/all-MiniLM-L6-v2** (preferred) with a **deterministic
  hash-based 384-dim fallback** (see `backend/app/services/embeddings.py`):
  the fallback hashes words into a bag-of-words vector so the app and tests run
  fully offline without downloading a model. Retrieval quality is lower with
  the fallback; install `sentence-transformers` for real semantic search.
  Both produce 384-dim L2-normalised vectors, so the FAISS index is identical.
- **FAISS IndexFlatIP**: exact inner-product search over normalised vectors
  (= cosine similarity), ideal for a small in-memory MVP index.
- **Groq SDK**: fast streaming LLM inference; model from `GROQ_MODEL`.

## Prerequisites

Python 3.12+, Node 20+, npm 10+. A Groq API key for live chat
(get one at https://console.groq.com — create an account, API Keys → Create).

## Installation

```bash
# Backend
cd devassist/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # then set GROQ_API_KEY in .env

# Frontend
cd ../frontend
npm install
```

## Environment configuration

Backend (`backend/.env`, see `backend/.env.example`):

```
GROQ_API_KEY=          # required for live chat; never commit
GROQ_MODEL=llama-3.3-70b-versatile   # UNVERIFIED default: confirm it exists
                                      # in the current Groq model catalogue
FRONTEND_ORIGIN=http://localhost:5173
MAX_UPLOAD_SIZE_MB=5
RAG_TOP_K=3
```

Frontend (optional, `frontend/.env`; no secrets): `VITE_API_URL=http://localhost:8000`,
`VITE_API_WS_URL=ws://localhost:8000/ws/chat`. Defaults already point there.

## Running

```bash
# Backend (port 8000)
cd devassist/backend && .venv/bin/python -m uvicorn app.main:app --port 8000
# Frontend (port 5173)
cd devassist/frontend && npm run dev
```

Open http://localhost:5173. Chat history lives in `sessionStorage` only.

## Tests

```bash
cd devassist/backend && .venv/bin/python -m pytest tests/ -q   # 22 tests, mocked Groq
cd devassist/frontend && npx vitest run                          # 12 tests
cd devassist/frontend && npx vue-tsc -b --noEmit && npm run build
```

No test requires a real Groq key. See `docs/TEST_REPORT.md` for actual results.

## API

| Method & path | Description |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /ready` | `{"status":"ready","embeddings":bool,"groq_configured":bool}` (never leaks the key) |
| `GET /documents` | List indexed documents: id, filename, size, chunks, status |
| `POST /upload` (multipart `file`) | Validates, extracts, chunks, indexes. Returns `{document_id, filename, size_bytes, chunks, status:"indexed"}`. Errors: 400 unsupported/empty/malformed, 413 over 5 MB |
| `DELETE /documents/{id}` | Removes document + rebuilds index. 404 if unknown |
| `WebSocket /ws/chat` | Client: `{"message": "..."}` (≤4000 chars). Server: `{"type":"token","token":...}`, `{"type":"done","sources":[{filename,page}]}`, or `{"type":"error","code":...,"message":...}`. Codes: `bad_request`, `groq_not_configured`, `rate_limited`, `provider_error` |

## Upload limits, chunking, retrieval

- Types: PDF, TXT, Markdown only. Max 5 MB (server-enforced). PDF must start
  with `%PDF`; TXT/MD must be valid UTF-8. Empty / text-less documents rejected.
- Chunking: ~500 characters with 50 characters of overlap, code indentation kept.
- Retrieval: top-K=3 chunks by cosine similarity; if nothing is indexed (or
  nothing relevant), the assistant answers from general programming knowledge
  without inventing document evidence. Citations show only real filenames and
  PDF page numbers tracked at ingestion.

## Known limitations

- Documents and chat history are in-memory / session-only: they disappear on
  backend restart or when the browser session ends.
- No authentication — do not expose the backend publicly without adding auth.
- The programming-only rule is a prompt-level behavioural boundary, not a
  security guarantee.
- `GROQ_MODEL` default is unverified against the live Groq catalogue.
- Live Groq streaming was not verified in this build (no key available);
  see `docs/TEST_REPORT.md`.
- With the hash embedding fallback, retrieval is vocabulary-overlap based,
  not semantic.

## Deployment guidance

Run the backend behind a reverse proxy with TLS, set `FRONTEND_ORIGIN` to the
real frontend origin, keep `GROQ_API_KEY` in the deployment environment (never
in the repo or frontend build), and put authentication in front if the service
is reachable beyond localhost. Frontend: `npm run build`, serve `dist/`.

## Security notes

See `docs/SECURITY.md` for the full checklist (key handling, CORS, upload
validation, Markdown sanitisation, untrusted document data, deletion safety).

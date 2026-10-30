# DevAssist Chatbot

A programming-specific AI assistant with Retrieval-Augmented Generation (RAG).
Ask programming questions, get streamed answers, and upload PDF / TXT / Markdown
technical documents to ask questions grounded in them.

## Features

- Streamed programming help: code debugging, code explanation, algorithms and
  data structures, APIs, databases, and software architecture
- Document-grounded answers: upload technical documents and ask questions
  about their contents
- Markdown rendering with syntax-highlighted code blocks and copy buttons
- Live indexing status for every uploaded document, plus one-click removal
- Programming-only scope: unrelated general-purpose requests are politely
  declined (a prompt-level rule, not a security guarantee)
- Session-only chat history: nothing is stored across browser sessions

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Vue 3 + TypeScript + Vite + Tailwind CSS | Small, typed, fast to build; styling is deliberate typography and spacing, not a component library |
| Markdown / code | marked + DOMPurify + highlight.js | Markdown rendered safely (HTML sanitised) with highlighted code |
| Backend | Python + FastAPI + Uvicorn | Typed schemas, async WebSocket support, fast to test |
| LLM | Groq SDK (streaming) | Fast streaming inference; model comes from `GROQ_MODEL` |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2, with a deterministic hash-based 384-dim fallback | The fallback lets the app and tests run fully offline without downloading a model; retrieval quality is lower with it, so install `sentence-transformers` for real semantic search. Both produce 384-dim L2-normalised vectors, so the FAISS index is identical |
| Vector store | FAISS IndexFlatIP (in-memory) | Exact inner-product search over normalised vectors (= cosine similarity), ideal for a small MVP index |

## Architecture and Data Flow

```
Browser (Vue 3 + TS) ──REST──▶ FastAPI backend ──▶ in-memory RagStore
  │  WebSocket /ws/chat (streaming tokens)            │  FAISS IndexFlatIP
  │  POST /upload, GET /documents, DELETE            │  (rebuilt on delete)
  └──────────────────────────────────────────────────▼
                                   Groq API (streaming chat, key server-side only)
```

1. **Upload** → validate (size / type / content) → extract text (PyMuPDF for
   PDF, UTF-8 for TXT / Markdown) → normalise (code indentation preserved) →
   chunk (~500 characters, 50 characters of overlap) → embed → store in FAISS
   with document ID + page (PDF) metadata.
2. **Chat** → embed the question with the same model → retrieve the top-K
   (default 3) chunks → build a bounded (≤ 4000 characters) document-context
   block, labelled as untrusted data → stream Groq tokens over WebSocket with
   a JSON envelope.
3. **Delete** → remove the document and rebuild the FAISS index from the
   remaining chunks, so deleted content is never retrieved again.

## Prerequisites

- Python 3.12+
- Node.js 20+ and npm 10+
- Git
- A Groq API key for live chat — get one at https://console.groq.com
  (create an account, then API Keys → Create API Key)

## Quickstart — Clone and Run Locally

```bash
git clone https://github.com/PeherSanghvi/DevAssist.git
cd DevAssist
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Open backend/.env and set your GROQ_API_KEY
```

### Frontend

```bash
cd ../frontend
npm install
```

### Run (two terminals)

```bash
# Terminal 1 — backend, http://localhost:8000
cd backend
python -m uvicorn app.main:app --port 8000 --env-file .env --reload

# Terminal 2 — frontend, http://localhost:5173
cd frontend
npm run dev
```

Open http://localhost:5173. Check the backend with
http://localhost:8000/health — it should return `{"status":"ok"}`.

`--env-file .env` is required so the backend receives `GROQ_API_KEY` from your
local `.env`. On Windows, `--reload` also avoids a uvicorn `WinError 64`
accept-loop crash seen with the default event loop.

## Environment Configuration

Backend (`backend/.env`, see `backend/.env.example`):

```
GROQ_API_KEY=          # required for live chat; never commit this file
GROQ_MODEL=openai/gpt-oss-120b
FRONTEND_ORIGIN=http://localhost:5173
MAX_UPLOAD_SIZE_MB=5
RAG_TOP_K=3
```

> **Model note:** `openai/gpt-oss-120b` is the verified model used by this
> project. Model availability depends on your Groq account; if Groq reports
> that the model does not exist, choose one listed in your Groq console and set
> it in `GROQ_MODEL`.

Frontend (optional, `frontend/.env` — no secrets here):

```
VITE_API_URL=http://localhost:8000
VITE_API_WS_URL=ws://localhost:8000/ws/chat
```

Both default to the local URLs above, so you can skip this file for local use.

## API Reference

| Method & path | Description |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /ready` | `{"status":"ready","embeddings":bool,"groq_configured":bool}` (never leaks the key) |
| `GET /documents` | List indexed documents: id, filename, size, chunks, status |
| `POST /upload` (multipart `file`) | Validates, extracts, chunks, indexes. Returns `{document_id, filename, size_bytes, chunks, status:"indexed"}`. Errors: 400 unsupported / empty / malformed, 413 over 5 MB |
| `DELETE /documents/{id}` | Removes the document and rebuilds the index. 404 if unknown |
| `WebSocket /ws/chat` | Client: `{"message": "..."}` (≤ 4000 characters). Server: `{"type":"token","token":...}`, `{"type":"done","sources":[{filename,page}]}`, or `{"type":"error","code":...,"message":...}`. Error codes: `bad_request`, `groq_not_configured`, `rate_limited`, `provider_error` |

## Upload Limits, Chunking and Retrieval

- **Types:** PDF, TXT, Markdown only. **Max size:** 5 MB (enforced server-side).
  A PDF must start with `%PDF`; TXT / Markdown must be valid UTF-8. Empty or
  text-less documents are rejected.
- **Chunking:** ~500 characters with 50 characters of overlap; code
  indentation is preserved.
- **Retrieval:** top-K = 3 chunks by cosine similarity. If nothing is indexed
  (or nothing relevant is found), the assistant answers from general
  programming knowledge without inventing document evidence. Citations show
  only real filenames and PDF page numbers tracked at ingestion.
- **Deletion safety:** deleting a document rebuilds the index, so its chunks
  can never be retrieved afterwards.

## Testing It With a Sample Document

Upload any short technical Markdown file, wait until it shows as indexed, then
ask questions whose answers only exist in that file — for example:

1. What is the retry policy for the payment service?
2. How long is the product catalogue cached for?
3. What happens after 5 consecutive failures?
4. What does `get_user(0)` do, and why?
5. What is the time complexity of binary search?

If the answers match the document, upload → indexing → retrieval is working.
A generic answer instead means the document context is not being picked up.

## Tests

```bash
# Backend (22 tests, Groq mocked — no real key needed)
cd backend && .venv/bin/python -m pytest tests/ -q

# Frontend (12 tests)
cd frontend && npx vitest run

# Frontend typecheck + production build
cd frontend && npm run build
```

No test requires a real Groq key. See `docs/TEST_REPORT.md` for recorded
results from the original build.

## Project Structure

```
DevAssist/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, health/ready/upload/delete/WS routes
│   │   ├── config.py          # Environment settings + programming-only system prompt
│   │   ├── schemas.py         # Typed request/response schemas
│   │   └── services/
│   │       ├── documents.py   # Upload validation + text extraction
│   │       ├── chunking.py    # 500-char chunks, 50-char overlap
│   │       ├── embeddings.py  # sentence-transformers with hash fallback
│   │       ├── rag_store.py   # FAISS index + deletion via rebuild
│   │       └── groq_client.py # Groq streaming + error mapping
│   ├── tests/                 # pytest suite (Groq mocked)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.vue            # Two-pane layout + welcome state
│       ├── components/        # Sidebar, ChatMessage, Composer, CodeBlock
│       ├── stores/chat.ts     # Session chat + document state
│       └── lib/               # REST client, WebSocket client, Markdown rendering
├── docs/
│   ├── SECURITY.md            # Security checklist
│   └── TEST_REPORT.md         # Recorded test and live-check results
└── README.md
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Chat returns `groq_not_configured` | Set a real `GROQ_API_KEY` in `backend/.env` and restart the backend |
| Groq says the model does not exist | Set `GROQ_MODEL` in `backend/.env` to a model listed in your Groq console |
| Frontend cannot reach the backend | Make sure the backend is running on port 8000, and `FRONTEND_ORIGIN` in `backend/.env` is `http://localhost:5173` |
| Upload rejected (400) | Check the file is PDF / TXT / Markdown, under 5 MB, and not empty |
| Upload rejected (413) | The file is over the 5 MB limit |
| Uploaded document answers disappear | Documents are in-memory only — restart the backend and they are gone; re-upload them |
| Port already in use | Stop the other process on port 8000 or 5173, or start the service on a different port and update the frontend URL |

## Known Limitations

- Documents and chat history are in-memory / session-only: they disappear on
  backend restart or when the browser session ends.
- No authentication — do not expose the backend publicly without adding auth.
- The programming-only rule is a prompt-level behavioural boundary, not a
  security guarantee.
- Live Groq streaming and the WebSocket flow were verified locally with a real
  API key and `openai/gpt-oss-120b`.
- With the hash embedding fallback, retrieval is vocabulary-overlap based,
  not semantic.

## Deployment Guidance

Run the backend behind a reverse proxy with TLS, set `FRONTEND_ORIGIN` to the
real frontend origin, keep `GROQ_API_KEY` in the deployment environment (never
in the repo or frontend build), and put authentication in front if the service
is reachable beyond localhost. Frontend: `npm run build`, then serve `dist/`.

## Security Notes

See `docs/SECURITY.md` for the full checklist: key handling, narrow CORS,
upload validation, Markdown sanitisation, untrusted document data, and
deletion safety.

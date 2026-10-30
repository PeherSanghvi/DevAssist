import io
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("GROQ_API_KEY", "")

from app.config import SYSTEM_PROMPT  # noqa: E402
from app.main import app, store  # noqa: E402
from app.services import groq_client  # noqa: E402
from app.services.chunking import chunk_text  # noqa: E402
from app.services.embeddings import DIM, embed_texts  # noqa: E402
from app.services.rag_store import RagStore  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    store.documents.clear()
    store.chunks.clear()
    store.index = None
    yield
    store.documents.clear()
    store.chunks.clear()
    store.index = None


def make_pdf_bytes(text="Python lists are mutable sequences. Sorting a list uses Timsort."):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_ready_no_key_leak():
    r = client.get("/ready")
    assert r.status_code == 200
    assert "GROQ_API_KEY" not in r.text and r.json()["groq_configured"] in (True, False)


def test_upload_txt():
    r = client.post("/upload", files={"file": ("notes.txt", b"Python debugging tips: use breakpoints and logging." * 20, "text/plain")})
    assert r.status_code == 200 and r.json()["status"] == "indexed" and r.json()["chunks"] >= 1


def test_upload_md():
    r = client.post("/upload", files={"file": ("doc.md", b"# Algorithms\n\nBinary search runs in O(log n) time.", "text/markdown")})
    assert r.status_code == 200 and r.json()["chunks"] >= 1


def test_upload_pdf():
    r = client.post("/upload", files={"file": ("doc.pdf", make_pdf_bytes(), "application/pdf")})
    assert r.status_code == 200 and r.json()["chunks"] >= 1


def test_unsupported_extension():
    r = client.post("/upload", files={"file": ("evil.exe", b"hello", "application/octet-stream")})
    assert r.status_code == 400


def test_oversized():
    big = b"x" * (5 * 1024 * 1024 + 1)
    r = client.post("/upload", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


def test_empty_document():
    r = client.post("/upload", files={"file": ("empty.txt", b"", "text/plain")})
    assert r.status_code == 400


def test_malformed_pdf():
    r = client.post("/upload", files={"file": ("bad.pdf", b"not a pdf at all", "application/pdf")})
    assert r.status_code == 400


def test_chunking_overlap():
    text = "abcdefghij" * 100  # 1000 chars
    chunks = chunk_text(text, size=500, overlap=50)
    assert len(chunks) == 3  # 0-500, 450-950, 900-1000
    assert chunks[1][:50] == chunks[0][-50:]
    assert all(len(c) <= 500 for c in chunks)


def test_embedding_dim():
    vecs = embed_texts(["hello world", "second doc"])
    assert vecs.shape == (2, DIM) == (2, 384)


def test_faiss_retrieval():
    s = RagStore()
    s.add_document("py.txt", 10, [(None, "Python lists are mutable and support append and sort methods.")])
    s.add_document("db.txt", 10, [(None, "PostgreSQL indexes speed up queries on large tables.")])
    hits = s.search("How do Python lists append and sort?", top_k=3)
    assert hits and hits[0]["filename"] == "py.txt"


def test_delete_and_retrieval_after_delete():
    s = RagStore()
    doc = s.add_document("py.txt", 10, [(None, "Python lists are mutable and support append.")])
    assert s.search("Python lists append", top_k=3)
    assert s.delete_document(doc.id) is True
    assert s.search("Python lists append", top_k=3) == []
    assert s.delete_document("nope") is False


def test_empty_index():
    assert RagStore().search("anything") == []


def test_delete_endpoint_404():
    assert client.delete("/documents/unknown123").status_code == 404


def test_programming_only_prompt():
    assert "programming" in SYSTEM_PROMPT.lower()
    assert "politely" in SYSTEM_PROMPT.lower()
    assert "untrusted" in SYSTEM_PROMPT.lower()


def test_ws_malformed_input():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("not json{")
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["code"] == "bad_request"


def test_ws_empty_message():
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "   "})
        assert ws.receive_json()["code"] == "bad_request"


async def _fake_stream(messages, model):
    yield "Hello "
    yield "world"


def test_ws_streaming_sequence(monkeypatch):
    monkeypatch.setattr(groq_client, "stream_chat", _fake_stream)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "Explain Python lists"})
        tokens = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "token":
                tokens.append(msg["token"])
            elif msg["type"] == "done":
                break
            else:
                raise AssertionError(msg)
        assert "".join(tokens) == "Hello world"


def test_ws_missing_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    # stream_chat reads env at call time via real function, but patch to raise the same error path
    async def _raise(messages, model):
        raise groq_client.GroqNotConfigured("missing")

        yield  # unreachable

    monkeypatch.setattr(groq_client, "stream_chat", _raise)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "hi"})
        assert ws.receive_json()["code"] == "groq_not_configured"


def test_ws_rate_limit(monkeypatch):
    async def _raise(messages, model):
        raise groq_client.GroqRateLimited("limited")

        yield

    monkeypatch.setattr(groq_client, "stream_chat", _raise)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "hi"})
        msg = ws.receive_json()
        assert msg["code"] == "rate_limited" and "10 seconds" not in msg["message"]


def test_ws_provider_error(monkeypatch):
    async def _raise(messages, model):
        raise groq_client.GroqProviderError("timed out")

        yield

    monkeypatch.setattr(groq_client, "stream_chat", _raise)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"message": "hi"})
        assert ws.receive_json()["code"] == "provider_error"

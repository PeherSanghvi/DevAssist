"""In-memory document registry + FAISS index.

Deletion is safe: FAISS IndexFlatIP has no reliable per-vector delete, so
deleting a document rebuilds the index from the remaining chunks.
"""
import uuid
from dataclasses import dataclass, field

import numpy as np

from .chunking import chunk_text, normalize_text
from .embeddings import DIM, embed_texts

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - fallback if faiss unavailable
    faiss = None


@dataclass
class Chunk:
    document_id: str
    filename: str
    page: int | None
    text: str
    embedding: np.ndarray = field(repr=False)


@dataclass
class Document:
    id: str
    filename: str
    size_bytes: int
    chunks: int
    status: str = "indexed"


class RagStore:
    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.chunks: list[Chunk] = []
        self.index = None

    def _rebuild(self):
        if faiss is None or not self.chunks:
            self.index = None
            return
        mat = np.stack([c.embedding for c in self.chunks]).astype(np.float32)
        index = faiss.IndexFlatIP(DIM)
        index.add(mat)
        self.index = index

    def add_document(self, filename: str, size_bytes: int, pages: list[tuple[int | None, str]]) -> Document:
        """pages: list of (page_number_or_None, page_text)."""
        doc_id = uuid.uuid4().hex[:12]
        all_chunks: list[Chunk] = []
        for page, page_text in pages:
            norm = normalize_text(page_text)
            for piece in chunk_text(norm):
                all_chunks.append(Chunk(document_id=doc_id, filename=filename, page=page, text=piece, embedding=np.zeros(DIM, dtype=np.float32)))
        if all_chunks:
            mat = embed_texts([c.text for c in all_chunks])
            for c, vec in zip(all_chunks, mat):
                c.embedding = vec
        doc = Document(id=doc_id, filename=filename, size_bytes=size_bytes, chunks=len(all_chunks))
        self.documents[doc_id] = doc
        self.chunks.extend(all_chunks)
        self._rebuild()
        return doc

    def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self.documents:
            return False
        del self.documents[doc_id]
        self.chunks = [c for c in self.chunks if c.document_id != doc_id]
        self._rebuild()
        return True

    def list_documents(self) -> list[Document]:
        return list(self.documents.values())

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.chunks or not query.strip():
            return []
        from .embeddings import embed_query

        q = embed_query(query).astype(np.float32)
        if self.index is not None:
            scores, idxs = self.index.search(q.reshape(1, -1), min(top_k, len(self.chunks)))
            results = []
            for score, idx in zip(scores[0], idxs[0]):
                if idx < 0:
                    continue
                c = self.chunks[int(idx)]
                results.append({"document_id": c.document_id, "filename": c.filename, "page": c.page, "snippet": c.text[:500], "score": float(score)})
            return results
        # Pure-python fallback (no faiss): cosine = dot of normalised vectors.
        scored = sorted(((float(np.dot(q, c.embedding)), c) for c in self.chunks), key=lambda x: x[0], reverse=True)
        return [{"document_id": c.document_id, "filename": c.filename, "page": c.page, "snippet": c.text[:500], "score": s} for s, c in scored[:top_k]]

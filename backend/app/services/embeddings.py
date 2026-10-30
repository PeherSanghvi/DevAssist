"""Embeddings: sentence-transformers when available, else a deterministic
hash-based fallback.

The fallback is NOT a semantic model: it hashes lower-cased words into a
384-dimensional bag-of-words vector (same dimension as all-MiniLM-L6-v2) and
L2-normalises it. It exists so the app and its tests run fully offline without
downloading a model, and so retrieval still ranks chunks sharing vocabulary
with the query. README documents this honestly; the real model is preferred
whenever it can be loaded.
"""
import hashlib
import re

import numpy as np

DIM = 384
_model = None
_model_tried = False


def _hash_embed(text: str) -> np.ndarray:
    vec = np.zeros(DIM, dtype=np.float32)
    for word in re.findall(r"[a-z0-9_]+", text.lower()):
        idx = int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIM
        vec[idx] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _load_model():
    global _model, _model_tried
    if _model_tried:
        return _model
    _model_tried = True
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        _model = None
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return L2-normalised float32 array of shape (n, 384)."""
    model = _load_model()
    if model is not None:
        vecs = model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)
    if not texts:
        return np.zeros((0, DIM), dtype=np.float32)
    return np.stack([_hash_embed(t) for t in texts]).astype(np.float32)


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def embeddings_available() -> bool:
    return _load_model() is not None

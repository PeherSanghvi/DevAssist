"""Text normalisation and chunking. Preserves code indentation."""
import re

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def normalize_text(text: str) -> str:
    # Normalise line endings and collapse 3+ blank lines; keep indentation.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Sliding-window chunks of ~`size` chars with `overlap` chars of overlap."""
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    step = size - overlap
    for start in range(0, len(text), step):
        chunk = text[start:start + size]
        if chunk.strip():
            chunks.append(chunk)
        if start + size >= len(text):
            break
    return chunks

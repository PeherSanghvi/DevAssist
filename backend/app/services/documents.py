"""Upload validation + text extraction. Uploaded content is untrusted."""
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def sniff_error(filename: str, data: bytes) -> str | None:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type '{ext or '(none)'}'. Upload PDF, TXT, or Markdown only."
    if not data:
        return "Uploaded file is empty."
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            return "Malformed PDF: file does not start with %PDF."
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return "File is not valid UTF-8 text."
    return None


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext == ".pdf":
        import fitz  # PyMuPDF

        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise ValueError("Malformed PDF: could not be parsed.") from exc
        pages = []
        for i, page in enumerate(doc):
            pages.append((i + 1, page.get_text()))
        doc.close()
        if not any(t.strip() for _, t in pages):
            raise ValueError("PDF contains no extractable text.")
        return pages
    text = data.decode("utf-8")
    if not text.strip():
        raise ValueError("Document contains no text.")
    return [(None, text)]

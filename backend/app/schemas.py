from pydantic import BaseModel


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    chunks: int
    status: str


class UploadOut(DocumentOut):
    pass

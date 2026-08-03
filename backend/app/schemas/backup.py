from pydantic import BaseModel


class BackupItemResponse(BaseModel):
    filename: str
    size: int
    created_at: str


class BackupDocumentResponse(BaseModel):
    name: str
    size: int
    modified_at: str

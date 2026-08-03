from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentLibraryCreateRequest(BaseModel):
    name: str
    description: str = ""
    directory: str = ""
    use_existing_directory: bool = False


class DocumentLibraryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    directory: Optional[str] = None


class DocumentLibraryResponse(BaseModel):
    id: int
    name: str
    description: str
    local_path: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: int
    library_id: int
    filename: str
    path: str
    uploaded_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class DocumentContentUpdateRequest(BaseModel):
    content: str

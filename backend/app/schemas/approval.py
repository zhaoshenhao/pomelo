from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ContentDiffItem(BaseModel):
    new: str
    old_doc_name: str
    old: str


class ContentDiff(BaseModel):
    new: list[str] = []
    conflict: list[ContentDiffItem] = []


class ApprovalJson(BaseModel):
    content_choice: str = "新增"
    replace_docs: list[str] = []
    content_diff: ContentDiff = ContentDiff()
    new_name: str = ""


class StageDocumentResponse(BaseModel):
    id: int
    library_id: int
    library_name: Optional[str] = None
    original_filename: str
    file_type: str
    stage_dir: str
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetaUpdateRequest(BaseModel):
    new_name: Optional[str] = None
    content_choice: Optional[str] = None
    replace_docs: Optional[list[str]] = None


class RewriteRequest(BaseModel):
    method: str
    style_id: Optional[int] = None


class PreviewSaveRequest(BaseModel):
    content: str

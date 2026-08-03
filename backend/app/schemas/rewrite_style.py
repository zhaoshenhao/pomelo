from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RewriteStyleCreateRequest(BaseModel):
    name: str
    prompt: str


class RewriteStyleUpdateRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None


class RewriteStyleResponse(BaseModel):
    id: int
    name: str
    prompt: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

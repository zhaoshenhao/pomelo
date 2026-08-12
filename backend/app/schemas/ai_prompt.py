from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

PromptType = Literal["rewrite", "study", "exam"]


class AIPromptCreateRequest(BaseModel):
    name: str
    prompt: str
    prompt_type: PromptType


class AIPromptUpdateRequest(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    prompt_type: Optional[PromptType] = None


class AIPromptResponse(BaseModel):
    id: int
    name: str
    prompt: str
    prompt_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

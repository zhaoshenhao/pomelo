from datetime import datetime

from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    id: int
    name: str
    user_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreateRequest(BaseModel):
    name: str


class TagUpdateRequest(BaseModel):
    name: str


class UserTagsUpdateRequest(BaseModel):
    tag_ids: list[int] = Field(default_factory=list)

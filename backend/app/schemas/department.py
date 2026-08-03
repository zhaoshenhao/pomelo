from datetime import datetime

from pydantic import BaseModel


class DepartmentCreateRequest(BaseModel):
    name: str


class DepartmentUpdateRequest(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    id: int
    name: str
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime

from pydantic import BaseModel


class QuestionBankGenerateRequest(BaseModel):
    name: str
    description: str = ""
    library_id: int
    document_names: list[str] = []
    prompt_id: int


class QuestionBankUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    disabled: bool | None = None


class QuestionBankResponse(BaseModel):
    id: int
    name: str
    description: str
    library_id: int
    library_name: str = ""
    document_names: str
    prompt_id: int
    created_by: int
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionBankListItem(BaseModel):
    id: int
    name: str
    description: str
    library_id: int
    library_name: str = ""
    document_names: str
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime
    disabled: bool = False
    question_count: int = 0
    type_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}


class QuestionBankListResponse(BaseModel):
    items: list[QuestionBankListItem]
    total: int
    page: int
    page_size: int

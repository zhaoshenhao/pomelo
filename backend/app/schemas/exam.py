from datetime import datetime

from pydantic import BaseModel


class ExamResponse(BaseModel):
    id: int
    name: str
    description: str
    duration_minutes: int
    pass_score: int
    created_by: int
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExamListItem(BaseModel):
    id: int
    name: str
    description: str
    duration_minutes: int
    pass_score: int
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExamListResponse(BaseModel):
    items: list[ExamListItem]
    total: int
    page: int
    page_size: int


class ExamUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    pass_score: int | None = None


class BankSelection(BaseModel):
    qb_id: int
    percentage: int = 0


class TypeSelection(BaseModel):
    type: str
    count: int
    score: int = 0


class ExamGenerateValidateRequest(BaseModel):
    name: str
    description: str = ""
    duration_minutes: int = 30
    pass_score: int = 60
    banks: list[BankSelection]
    types: list[TypeSelection]


class CrossCell(BaseModel):
    count: int = 0


class CrossTableRow(BaseModel):
    qb_id: int
    qb_name: str = ""
    cells: list[CrossCell]
    total: int = 0


class TypeScoreRow(BaseModel):
    per_score: int
    count: int
    total_score: int


class ExamGenerateValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = []
    cross_table: list[CrossTableRow] = []
    type_table: list[TypeScoreRow] = []
    total_questions: int = 0
    total_score: int = 0
    duration_minutes: int = 0
    pass_score: int = 0


class ExamGenerateRequest(BaseModel):
    name: str
    description: str = ""
    duration_minutes: int = 30
    pass_score: int = 60
    banks: list[BankSelection]
    types: list[TypeSelection]


class ExamBatchCreateRequest(BaseModel):
    name: str | None = None
    description: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    pass_score: int | None = None
    tag_ids: list[int] = []
    student_ids: list[int] = []
    exclude_completed_days: int = 60


class ExamBatchUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    pass_score: int | None = None
    disabled: bool | None = None


class ExamBatchResponse(BaseModel):
    id: int
    exam_id: int
    arranged_by: int
    arranged_by_name: str = ""
    name: str | None = None
    description: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    pass_score: int | None = None
    disabled: bool = False
    arranged_count: int = 0
    completed_count: int = 0
    pass_rate: float | None = None
    average_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExamBatchListResponse(BaseModel):
    batches: list[ExamBatchResponse]


class BatchStudentAddRequest(BaseModel):
    student_id: int


class AssignmentResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    student_name: str = ""
    batch_id: int = 0
    status: str
    score: float | None = None
    passed: bool | None = None
    correct: int = 0
    total: int = 0
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExamBatchDetailResponse(BaseModel):
    id: int
    exam_id: int
    arranged_by: int
    arranged_by_name: str = ""
    name: str | None = None
    description: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    pass_score: int | None = None
    disabled: bool = False
    created_at: datetime
    students: list[AssignmentResponse] = []


class ExamSubmitRequest(BaseModel):
    answers: list[dict]


class ExamSubmitResponse(BaseModel):
    completed: int
    correct: int
    total: int
    score: float
    passed: bool
    evaluation: str = ""


class ExamResultResponse(BaseModel):
    total_students: int
    average_score: float
    pass_rate: float
    per_question_accuracy: list[dict] = []
    knowledge_coverage: str = ""


class ExamTakeResponse(BaseModel):
    id: int
    name: str
    description: str
    duration_minutes: int
    pass_score: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    questions: list[dict]

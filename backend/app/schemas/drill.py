from pydantic import BaseModel


class DrillBankItem(BaseModel):
    id: int
    name: str
    description: str
    question_count: int
    type_counts: dict[str, int]
    total_answered: int = 0
    correct_count: int = 0
    accuracy: float = 0.0
    ever_correct_questions: int = 0

    model_config = {"from_attributes": True}


class DrillSessionStartRequest(BaseModel):
    qb_id: int


class DrillSessionStartResponse(BaseModel):
    session_id: str
    qb_id: int
    qb_name: str = ""
    questions: list[dict]


class DrillAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: object


class DrillAnswerResponse(BaseModel):
    correct: bool
    correct_answer: object
    explanation: str
    tested: int
    accuracy: float


class DrillQuestionStat(BaseModel):
    question_id: str
    type: str
    question: str
    total_attempts: int
    correct: int
    accuracy: float


class DrillBankSummary(BaseModel):
    qb_id: int
    qb_name: str
    total_students: int
    used_questions: int
    total_attempts: int
    ever_correct_questions: int
    total_correct: int
    accuracy: float
    updated_at: str
    questions: list[DrillQuestionStat]

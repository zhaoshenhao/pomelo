from pydantic import BaseModel


class DashboardCounts(BaseModel):
    documents: int
    students: int
    teachers: int
    admins: int
    departments: int
    question_banks: int
    study_materials: int
    exams: int


class RecentExamInfo(BaseModel):
    exam_id: int
    batch_id: int
    name: str
    start_time: str | None
    end_time: str | None
    duration_minutes: int
    pass_score: int
    question_count: int
    type_counts: dict[str, int]
    arranged_count: int
    completed_count: int | None
    pass_rate: float | None
    average_score: float | None
    started: bool
    ended: bool


class StudyProgressInfo(BaseModel):
    material_id: int
    name: str
    min_minutes: int
    started_count: int
    completed_count: int
    total_study_seconds: int
    avg_study_seconds: float
    avg_read_count: float


class TeacherDashboardResponse(BaseModel):
    counts: DashboardCounts
    recent_exams: list[RecentExamInfo]
    study_progress: list[StudyProgressInfo]


class StudentExamInfo(BaseModel):
    assignment_id: int | None
    exam_id: int
    batch_id: int | None
    name: str
    start_time: str | None
    end_time: str | None
    duration_minutes: int
    pass_score: int
    question_count: int
    type_counts: dict[str, int]
    status: str
    score: float | None
    passed: bool | None


class StudentCourseInfo(BaseModel):
    material_id: int
    material_name: str
    material_description: str
    document_names: str
    min_minutes: int
    has_started: bool
    completed: bool
    total_study_seconds: int
    last_study_at: str | None
    assignment_id: int | None


class StudentDrillInfo(BaseModel):
    id: int
    name: str
    description: str
    question_count: int
    type_counts: dict[str, int]
    total_answered: int
    correct_count: int
    accuracy: float
    ever_correct_questions: int


class StudentDashboardResponse(BaseModel):
    exams: list[StudentExamInfo]
    courses: list[StudentCourseInfo]
    drills: list[StudentDrillInfo]

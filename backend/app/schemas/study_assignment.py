
from pydantic import BaseModel


class StudyProgressRequest(BaseModel):
    seconds: int


class StudyAssignmentStartResponse(BaseModel):
    id: int
    material_id: int
    material_name: str = ""
    material_description: str = ""
    min_minutes: int = 10
    total_study_seconds: int = 0
    completed: bool = False
    pages: list[dict] = []

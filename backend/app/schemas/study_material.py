from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StudyMaterialGenerateRequest(BaseModel):
    name: str
    description: str = ""
    library_id: int
    document_names: list[str] = []
    prompt_id: int


class StudyMaterialUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    min_minutes: Optional[int] = None


class StudyMaterialResponse(BaseModel):
    id: int
    name: str
    description: str
    library_id: int
    library_name: str = ""
    document_names: str
    prompt_id: int
    voice: str = ""
    active: bool = True
    read_count: int = 0
    complete_count: int = 0
    min_minutes: int = 10
    created_by: int
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyMaterialListItem(BaseModel):
    id: int
    name: str
    description: str
    library_id: int
    library_name: str = ""
    document_names: str
    voice: str = ""
    active: bool = True
    read_count: int = 0
    complete_count: int = 0
    min_minutes: int = 10
    creator_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyMaterialListResponse(BaseModel):
    items: list[StudyMaterialListItem]
    total: int
    page: int
    page_size: int


class ManifestPage(BaseModel):
    type: str
    chapter: Optional[int] = None
    page: Optional[int] = None
    title: str
    file: str
    text_file: str
    audio_file: Optional[str] = None
    audio_duration: Optional[float] = None


class StudyMaterialDetailResponse(StudyMaterialResponse):
    pages: list[ManifestPage] = []


class VoiceRequest(BaseModel):
    voice: str


class StudyMaterialSummaryStats(BaseModel):
    material_id: int
    material_name: str
    students_viewed: int = 0
    students_completed: int = 0
    total_open_count: int = 0
    total_watch_seconds: int = 0
    avg_watch_seconds: float = 0.0


class StudyMaterialStudentItem(BaseModel):
    student_id: int
    name: str
    viewed: bool = False
    completed: bool = False
    total_study_seconds: int = 0
    read_count: int = 0
    complete_count: int = 0

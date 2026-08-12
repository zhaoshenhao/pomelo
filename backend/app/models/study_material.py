from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class StudyMaterial(Base):
    __tablename__ = "study_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    library_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("document_libraries.id"), nullable=False, index=True
    )
    document_names: Mapped[str] = mapped_column(Text, default="")
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_prompts.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    voice: Mapped[str] = mapped_column(String(100), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    complete_count: Mapped[int] = mapped_column(Integer, default=0)
    min_minutes: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class QuestionBank(Base):
    __tablename__ = "qb"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("document_libraries.id"), nullable=False)
    document_names: Mapped[str] = mapped_column(Text, default="")
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_prompts.id"), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __mapper_args__ = {"eager_defaults": True}


from app.models.user import User  # noqa: F401, E402
from app.models.department import Department  # noqa: F401, E402
from app.models.document import Document, DocumentLibrary  # noqa: F401, E402
from app.models.stage_document import StageDocument  # noqa: F401, E402
from app.models.ai_prompt import AIPrompt  # noqa: F401, E402
from app.models.study_material import StudyMaterial  # noqa: F401, E402
from app.models.exam import Exam, ExamAssignment, ExamBatch  # noqa: F401, E402
from app.models.study_assignment import StudyAssignment  # noqa: F401, E402
from app.models.student_tag import StudentTag  # noqa: F401, E402
from app.models.question_bank import QuestionBank  # noqa: F401, E402
from app.models.video import Video, VideoComment, VideoViewRecord  # noqa: F401, E402


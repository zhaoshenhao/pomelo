from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.user import User  # noqa: F401, E402
from app.models.department import Department  # noqa: F401, E402
from app.models.document import Document, DocumentLibrary  # noqa: F401, E402
from app.models.stage_document import StageDocument  # noqa: F401, E402
from app.models.rewrite_style import RewriteStyle  # noqa: F401, E402


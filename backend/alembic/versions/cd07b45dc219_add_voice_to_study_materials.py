"""add_voice_to_study_materials

Revision ID: cd07b45dc219
Revises: 28c7bc19b5b2
Create Date: 2026-08-05 14:49:02.756796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd07b45dc219'
down_revision: Union[str, None] = '28c7bc19b5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("study_materials", sa.Column("voice", sa.String(100), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("study_materials", "voice")

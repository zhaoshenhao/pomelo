"""allow_null_library_id_on_videos

Revision ID: b079dade0976
Revises: 13d8c7950de6
Create Date: 2026-08-11 14:12:45.844752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b079dade0976'
down_revision: Union[str, None] = '13d8c7950de6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('videos', 'library_id',
               existing_type=sa.Integer(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('videos', 'library_id',
               existing_type=sa.Integer(),
               nullable=False)

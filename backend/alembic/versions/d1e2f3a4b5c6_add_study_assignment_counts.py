"""add_study_assignment_counts

Revision ID: d1e2f3a4b5c6
Revises: b079dade0976
Create Date: 2026-08-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'b079dade0976'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('study_assignments', sa.Column('read_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('study_assignments', sa.Column('complete_count', sa.Integer(), nullable=False, server_default=sa.text('0')))

    # Backfill existing rows: every existing assignment has been opened at least once.
    op.execute("UPDATE study_assignments SET read_count = 1 WHERE read_count = 0")
    op.execute("UPDATE study_assignments SET complete_count = 1 WHERE status = 'completed' AND complete_count = 0")


def downgrade() -> None:
    op.drop_column('study_assignments', 'complete_count')
    op.drop_column('study_assignments', 'read_count')

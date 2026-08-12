"""add_exams_and_assignments

Revision ID: a3c455ab807e
Revises: cd07b45dc219
Create Date: 2026-08-05 20:20:44.229818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c455ab807e'
down_revision: Union[str, None] = 'cd07b45dc219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('exams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('library_id', sa.Integer(), nullable=False),
        sa.Column('document_names', sa.Text(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('pass_score', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['library_id'], ['document_libraries.id']),
        sa.ForeignKeyConstraint(['prompt_id'], ['ai_prompts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table('exam_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='assigned'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'student_id'),
    )
    op.create_index(op.f('ix_exam_assignments_exam_id'), 'exam_assignments', ['exam_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_exam_assignments_exam_id'), table_name='exam_assignments')
    op.drop_table('exam_assignments')
    op.drop_table('exams')

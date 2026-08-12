"""add_study_materials

Revision ID: c1d2e3f4g5h6
Revises: b1e2f3d4e5f6
Create Date: 2026-08-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, None] = 'b1e2f3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('study_materials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('library_id', sa.Integer(), nullable=False),
        sa.Column('document_names', sa.Text(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['library_id'], ['document_libraries.id']),
        sa.ForeignKeyConstraint(['prompt_id'], ['ai_prompts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_materials_library_id'), 'study_materials', ['library_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_study_materials_library_id'), table_name='study_materials')
    op.drop_table('study_materials')

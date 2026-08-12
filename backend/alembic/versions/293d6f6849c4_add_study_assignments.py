"""add_study_assignments

Revision ID: 293d6f6849c4
Revises: dea789ecaa1e
Create Date: 2026-08-06 16:45:46.753216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '293d6f6849c4'
down_revision: Union[str, None] = 'dea789ecaa1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('study_material_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('study_materials.id'), nullable=False),
        sa.Column('arranged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_study_material_batches_material_id'), 'study_material_batches', ['material_id'], unique=False)

    op.create_table('study_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('study_materials.id'), nullable=False),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('batch_id', sa.Integer(), sa.ForeignKey('study_material_batches.id'), nullable=False),
        sa.Column('min_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='assigned'),
        sa.Column('has_started', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('total_study_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_study_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material_id', 'student_id'),
    )
    op.create_index(op.f('ix_study_assignments_material_id'), 'study_assignments', ['material_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_study_assignments_material_id'), table_name='study_assignments')
    op.drop_table('study_assignments')
    op.drop_index(op.f('ix_study_material_batches_material_id'), table_name='study_material_batches')
    op.drop_table('study_material_batches')

"""simplify_study_assignments

Revision ID: 1ce03174fd08
Revises: 293d6f6849c4
Create Date: 2026-08-06 17:29:40.857104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ce03174fd08'
down_revision: Union[str, None] = '293d6f6849c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('study_assignments_ibfk_3', 'study_assignments', type_='foreignkey')
    op.drop_column('study_assignments', 'batch_id')
    op.drop_column('study_assignments', 'has_started')
    op.drop_column('study_assignments', 'min_minutes')
    op.drop_column('study_assignments', 'completed_at')

    op.add_column('study_materials', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')))
    op.add_column('study_materials', sa.Column('read_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('study_materials', sa.Column('complete_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('study_materials', sa.Column('min_minutes', sa.Integer(), nullable=False, server_default=sa.text('10')))

    op.drop_table('study_material_batches')


def downgrade() -> None:
    op.create_table('study_material_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('arranged_by', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_study_material_batches_material_id'), 'study_material_batches', ['material_id'], unique=False)

    op.drop_column('study_materials', 'min_minutes')
    op.drop_column('study_materials', 'complete_count')
    op.drop_column('study_materials', 'read_count')
    op.drop_column('study_materials', 'active')

    op.add_column('study_assignments', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('study_assignments', sa.Column('has_started', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('study_assignments', sa.Column('min_minutes', sa.Integer(), nullable=False, server_default=sa.text('10')))
    op.add_column('study_assignments', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.create_foreign_key('study_assignments_ibfk_3', 'study_assignments', 'study_material_batches', ['batch_id'], ['id'])

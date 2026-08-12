"""split_exams_to_qb_and_exam

Revision ID: 1382e9d14ecb
Revises: 9b0cf86ad4f7
Create Date: 2026-08-08 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1382e9d14ecb'
down_revision: Union[str, None] = '9b0cf86ad4f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET FOREIGN_KEY_CHECKS = 0")

    op.drop_table('exam_assignments')
    op.drop_table('exam_batches')

    op.execute("ALTER TABLE exams RENAME TO qb")
    op.execute("ALTER TABLE qb DROP COLUMN duration_minutes")
    op.execute("ALTER TABLE qb DROP COLUMN pass_score")

    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('pass_score', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'exam_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('arranged_by', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('pass_score', sa.Integer(), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['arranged_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_batches_exam_id'), 'exam_batches', ['exam_id'])

    op.create_table(
        'exam_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='assigned'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['exam_batches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'student_id'),
    )
    op.create_index(op.f('ix_exam_assignments_exam_id'), 'exam_assignments', ['exam_id'])

    op.execute("SET FOREIGN_KEY_CHECKS = 1")


def downgrade() -> None:
    op.execute("SET FOREIGN_KEY_CHECKS = 0")

    op.drop_table('exam_assignments')
    op.drop_table('exam_batches')
    op.drop_table('exams')

    op.execute("ALTER TABLE qb ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30")
    op.execute("ALTER TABLE qb ADD COLUMN pass_score INTEGER NOT NULL DEFAULT 60")
    op.execute("ALTER TABLE qb RENAME TO exams")

    op.create_table(
        'exam_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('arranged_by', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['arranged_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_batches_exam_id'), 'exam_batches', ['exam_id'])

    op.create_table(
        'exam_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='assigned'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['exam_batches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'student_id'),
    )
    op.create_index(op.f('ix_exam_assignments_exam_id'), 'exam_assignments', ['exam_id'])

    op.execute("SET FOREIGN_KEY_CHECKS = 1")

"""add_exam_batches

Revision ID: dea789ecaa1e
Revises: a3c455ab807e
Create Date: 2026-08-06 11:38:13.808449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dea789ecaa1e'
down_revision: Union[str, None] = 'a3c455ab807e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('exam_batches',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id'), nullable=False),
        sa.Column('arranged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exam_batches_exam_id'), 'exam_batches', ['exam_id'], unique=False)

    op.add_column('exam_assignments', sa.Column('batch_id', sa.Integer(), nullable=True))

    # backfill: group existing assignments by (exam_id, deadline)
    conn = op.get_bind()
    # get distinct (exam_id, deadline) groups from assignments
    rows = conn.execute(sa.text(
        "SELECT exam_id, deadline FROM exam_assignments GROUP BY exam_id, deadline"
    )).fetchall()
    for r in rows:
        exam_id, deadline = r[0], r[1]
        # get arranged_by from exam creator
        creator = conn.execute(
            sa.text("SELECT created_by FROM exams WHERE id = :eid"),
            {"eid": exam_id}
        ).scalar()
        if creator is None:
            continue
        # insert batch
        result = conn.execute(
            sa.text("INSERT INTO exam_batches (exam_id, arranged_by, deadline) VALUES (:eid, :uid, :dl)"),
            {"eid": exam_id, "uid": creator, "dl": deadline}
        )
        batch_id = result.lastrowid
        # update assignments
        conn.execute(
            sa.text("UPDATE exam_assignments SET batch_id = :bid WHERE exam_id = :eid AND (deadline = :dl OR (deadline IS NULL AND :dl IS NULL))"),
            {"bid": batch_id, "eid": exam_id, "dl": deadline}
        )

    op.alter_column('exam_assignments', 'batch_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(None, 'exam_assignments', 'exam_batches', ['batch_id'], ['id'])
    op.drop_column('exam_assignments', 'deadline')


def downgrade() -> None:
    op.add_column('exam_assignments', sa.Column('deadline', sa.DateTime(), nullable=True))
    op.drop_constraint(None, 'exam_assignments', type_='foreignkey')
    op.drop_column('exam_assignments', 'batch_id')
    op.drop_index(op.f('ix_exam_batches_exam_id'), table_name='exam_batches')
    op.drop_table('exam_batches')

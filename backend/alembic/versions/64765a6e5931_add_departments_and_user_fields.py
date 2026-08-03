"""add_departments_and_user_fields

Revision ID: 64765a6e5931
Revises: 268a4847fea2
Create Date: 2026-07-31 15:19:00.389330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = '64765a6e5931'
down_revision: Union[str, None] = '268a4847fea2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('departments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.add_column('users', sa.Column('display_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('department_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'departments', ['department_id'], ['id'])

    conn = op.get_bind()
    result = conn.execute(text("SELECT DISTINCT department FROM users WHERE department IS NOT NULL AND department != ''"))
    departments = [row[0] for row in result]
    for dept_name in departments:
        conn.execute(text("INSERT IGNORE INTO departments (name) VALUES (:name)"), {"name": dept_name})

    conn.execute(text("""
        UPDATE users u
        JOIN departments d ON u.department = d.name
        SET u.department_id = d.id
    """))

    conn.execute(text("UPDATE users SET display_name = username WHERE display_name IS NULL"))

    op.drop_column('users', 'department')


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE users u
        JOIN departments d ON u.department_id = d.id
        SET u.department = d.name
    """))

    op.add_column('users', sa.Column('department', mysql.VARCHAR(length=100), nullable=False))
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'department_id')
    op.drop_column('users', 'display_name')
    op.drop_table('departments')

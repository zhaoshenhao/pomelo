"""add_disabled_to_qb

Revision ID: 1e5b049e0e9c
Revises: a218e4d82bfe
Create Date: 2026-08-10 16:17:03.243149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1e5b049e0e9c'
down_revision: Union[str, None] = 'a218e4d82bfe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('qb', sa.Column('disabled', sa.Boolean(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    op.drop_column('qb', 'disabled')

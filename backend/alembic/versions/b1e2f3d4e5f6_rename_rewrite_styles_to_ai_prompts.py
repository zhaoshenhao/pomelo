"""rename_rewrite_styles_to_ai_prompts

Revision ID: b1e2f3d4e5f6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1e2f3d4e5f6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table('rewrite_styles', 'ai_prompts')
    op.add_column('ai_prompts', sa.Column(
        'prompt_type', sa.String(length=20), nullable=False, server_default=sa.text("'rewrite'")
    ))
    op.drop_index('name', table_name='ai_prompts')
    op.create_unique_constraint('uq_ai_prompts_type_name', 'ai_prompts', ['prompt_type', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_ai_prompts_type_name', 'ai_prompts', type_='unique')
    op.create_unique_constraint('name', 'ai_prompts', ['name'])
    op.drop_column('ai_prompts', 'prompt_type')
    op.rename_table('ai_prompts', 'rewrite_styles')

"""add_videos

Revision ID: 13d8c7950de6
Revises: 1e5b049e0e9c
Create Date: 2026-08-11 11:36:50.511841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '13d8c7950de6'
down_revision: Union[str, None] = '1e5b049e0e9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('videos',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('library_id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('oss_path', sa.String(length=500), nullable=False),
    sa.Column('original_filename', sa.String(length=500), nullable=False),
    sa.Column('total_views', sa.Integer(), nullable=False),
    sa.Column('total_watch_seconds', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['library_id'], ['document_libraries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_library_id'), 'videos', ['library_id'], unique=False)
    op.create_table('video_comments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('video_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_comments_video_id'), 'video_comments', ['video_id'], unique=False)
    op.create_table('video_view_records',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('video_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('watch_seconds', sa.Integer(), nullable=False),
    sa.Column('watched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_view_records_video_id'), 'video_view_records', ['video_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_video_view_records_video_id'), table_name='video_view_records')
    op.drop_table('video_view_records')
    op.drop_index(op.f('ix_video_comments_video_id'), table_name='video_comments')
    op.drop_table('video_comments')
    op.drop_index(op.f('ix_videos_library_id'), table_name='videos')
    op.drop_table('videos')

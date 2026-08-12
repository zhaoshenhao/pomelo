"""update_study_style_prompt

Revision ID: 28c7bc19b5b2
Revises: c1d2e3f4g5h6
Create Date: 2026-08-04 19:07:38.129367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c7bc19b5b2'
down_revision: Union[str, None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PROMPT = (
    "现代科技风格设计，具体视觉要求：\n"
    "- 配色：深蓝色系为主色，搭配亮青色/电光蓝作为强调色。深色渐变背景，亮色前景文字，营造高端科技感\n"
    "- 卡片：内容以圆角卡片呈现，白色/半透明背景、微妙阴影和发光边框。卡片间距适中\n"
    "- 标题：大号黑粗字体，可用渐变文字效果或亮色强调\n"
    "- 页面布局：居中排版，像一页PPT幻灯片。封面页标题放大居中，章节页有醒目的章节编号\n"
    "- 动效：元素载入时从小到大淡入，卡片hover时轻微浮动\n"
    "- 背景：深色调，带几何线条或网格纹理的渐变，整洁有秩序感\n"
)

OLD_PROMPT = (
    "简洁，有科技感的格式。通过CSS等现代技术实现，但不要引入第三方库，必须全部嵌入页面内。\n"
    "页面做得像PPT，需要有 Title，黑粗，字体较大。\n"
    "页面有最小尺寸，最大尺寸随工作区而变大，但是周围要有边框\n"
    "整个页面被框起来，选择合适的边框风格和页面。\n"
    "需要有一个合适的背景，带现代风格。\n"
)


def upgrade() -> None:
    op.execute(sa.text("UPDATE ai_prompts SET prompt = :p WHERE id = 3").bindparams(p=NEW_PROMPT))


def downgrade() -> None:
    op.execute(sa.text("UPDATE ai_prompts SET prompt = :p WHERE id = 3").bindparams(p=OLD_PROMPT))

import logging
import os

import yaml

logger = logging.getLogger(__name__)

_prompts_cache: dict[str, str] | None = None

GRAMMAR_REWRITE_DEFAULT = (
    "请修正下列文本中的错别字和语法不通顺的地方，"
    "保持原意和Markdown格式（包括标题、列表、表格、代码块等）不变。"
    "只修正语言错误，不要改变内容结构或风格。"
    "只输出修正后的文本，不要添加任何说明。"
)

STUDY_MATERIAL_DEFAULT = (
    "你是一个教育内容设计专家。请根据提供的学习资料，生成一份结构化的学习材料。\n\n"
    "── 页面样式（应用于全部页面）──\n"
    "你需要首先输出一套完整的 CSS 样式，这套样式将应用于该学习资料的所有页面。\n"
    "样式要求：颜色丰富、视觉生动、有现代设计感，可包含：渐变背景、彩色标题、卡片圆角与阴影、徽章、高亮块、提示框、边框装饰、keyframes 载入动效等。\n"
    "使用以下预定义组件类来组织页面内容：.card（卡片）、.highlight（高亮块）、.callout（提示框）、.grid（多列布局）、.badge（徽章）、.stat（数据展示块）。\n"
    "页面整体可以有一个协调的配色方案和氛围。\n\n"
    "── 内容结构 ──\n"
    "1. 封面：标题（h1）+ 简短概述（可用 .highlight 或 .callout 包装），内容用 .card 等组件组织\n"
    "2. 主体章节（2-5个），每个章节：\n"
    "   - 章节封面：章节标题（h2）+ 本章摘要（可用 .card 或 .highlight）\n"
    "   - 章节页面（1-3个）：使用 .card/.grid/.badge/.stat/.callout/.highlight 等组件呈现内容，允许内联 style 补充效果\n"
    "3. 结束页：学习总结（可用 .card 或 blockquote）\n\n"
    "── 标签与类名 ──\n"
    "- 允许使用 div, section, span, table 等语义标签\n"
    "- 内容使用上述预定义组件类（.card, .highlight, .callout, .grid, .badge, .stat）组织\n"
    "- 允许在元素上添加内联 style 属性（颜色、渐变、间距等）\n"
    "- 不要包含 <html> 或 <body> 标签\n"
    "- 图片链接用 img 标签保留\n\n"
    "── 朗读文本 ──\n"
    "每个页面提供 narration 字段，内容口语化、纯文本、不含 HTML。\n\n"
    "── 输出格式 ──\n"
    "严格按以下 JSON 输出，不要任何 markdown 标记或额外文字：\n"
    '{\n'
    '  "style": "一套完整CSS样式，应用于所有页面 { 配色、渐变、卡片、高亮、徽章、边框、动效keyframes等 }",\n'
    '  "cover": {"title": "标题", "description": "封面内容html", "narration": "朗读文本"},\n'
    '  "chapters": [\n'
    '    {\n'
    '      "title": "章节标题",\n'
    '      "summary": "章节摘要html",\n'
    '      "narration": "朗读文本",\n'
    '      "pages": [\n'
    '        {"title": "页面标题", "content": "页面内容html", "narration": "朗读文本"}\n'
    '      ]\n'
    '    }\n'
    '  ],\n'
    '  "end": {"title": "结束标题", "content": "结束内容html", "narration": "朗读文本"}\n'
    '}\n\n'
    "style 字段的 CSS 需遵循：\n"
    "- 不要包含 @import 或 url() 引用外部资源\n"
    "- 可以有 @keyframes 动画和对应的 animation 属性\n"
    "- 可以给 .card, .highlight, .callout, .grid, .badge, .stat 等组件定义样式（与内容使用的类名对应）\n"
    "- 可以给 body.cover, body.chapter-cover, body.end, body.page 定义该页面类型特有的背景或布局\n"
)

EXAM_DEFAULT = (
    "你是一位教育考试设计专家。请根据提供的参考文档，出一套高质量的考试题。\n\n"
    "题型要求：\n"
    "- 填空(fill)：填写关键术语或概念，答案唯一明确\n"
    "- 对错(true_false)：判断命题对错，答案 true 或 false\n"
    "- 单选(single)：4个选项，仅1个正确答案\n"
    "- 多选(multiple)：4个选项，至少2个正确答案\n"
    "- 匹配(match)：左右两列，一一对应匹配\n\n"
    "注意：type 字段只能使用以下值之一：fill、true_false、single、multiple、match。绝对禁止使用其他值（如 essay、field、short_answer 等）。\n\n"
    "题量：请严格按照下方「出题要求」中指定的题目数量和题型出题；若出题要求未指定数量，则根据文档内容合理出题（5-20题），题型分散，难易结合。\n\n"
    "每道题格式：\n"
    '{\n'
    '  "id": "q1",\n'
    '  "type": "single|multiple|true_false|fill|match",\n'
    '  "question": "题干文字（必要时包含上下文）",\n'
    '  "options": ["A选项","B选项","C选项","D选项"],\n'
    '  "answer": "A",\n'
    '  "answers": ["A","C"],\n'
    '  "matches": {"A":"1","B":"2"},\n'
    '  "left": ["A","B"],\n'
    '  "right": ["1","2"],\n'
    '  "explanation": "答案解释"\n'
    '}\n\n'
    "所有题目的选项用 A/B/C/D 字母标识。\n\n"
    "严格按以下 JSON 格式输出，不要添加任何 markdown 标记或额外文字：\n"
    '{\n'
    '  "questions": [\n'
    '    {"id":"q1","type":"single","question":"...","options":["A.","B.","C.","D."],"answer":"A","explanation":"..."},\n'
    '    {"id":"q2","type":"fill","question":"...","answer":"标准答案","explanation":"..."},\n'
    '    {"id":"q3","type":"true_false","question":"...","answer":true,"explanation":"..."},\n'
    '    {"id":"q4","type":"multiple","question":"...","options":["...","...","...","..."],"answers":["A","C"],"explanation":"..."},\n'
    '    {"id":"q5","type":"match","question":"...","left":["A","B","C"],"right":["1","2","3"],"matches":{"A":"1","B":"2","C":"3"},"explanation":"..."}\n'
    '  ]\n'
    '}\n'
)

_BUILTIN = {
    "grammar_rewrite_prompt": GRAMMAR_REWRITE_DEFAULT,
    "study_material_prompt": STUDY_MATERIAL_DEFAULT,
    "exam_prompt": EXAM_DEFAULT,
}


def _resolve_prompts_file(relative_path: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.normpath(os.path.join(base, relative_path))


def load_prompts(prompts_file: str = "") -> dict[str, str]:
    global _prompts_cache
    if _prompts_cache is not None:
        return _prompts_cache

    resolved = prompts_file or ""

    if resolved and not os.path.isabs(resolved):
        resolved = _resolve_prompts_file(resolved)

    if resolved and os.path.isfile(resolved):
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                result = {}
                for key in ("grammar_rewrite_prompt", "study_material_prompt", "exam_prompt"):
                    val = data.get(key, "")
                    if isinstance(val, str) and val.strip():
                        result[key] = val.strip()
                    else:
                        result[key] = _BUILTIN[key]
                _prompts_cache = result
                logger.info("Prompts loaded from %s", resolved)
                return result
        except Exception as e:
            logger.warning("Failed to load prompts from %s: %s", resolved, e)

    _prompts_cache = dict(_BUILTIN)
    return _prompts_cache


def get_prompts() -> dict[str, str]:
    from app.config import settings

    return load_prompts(settings.PROMPTS_FILE)

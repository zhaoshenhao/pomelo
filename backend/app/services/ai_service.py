import json
import logging

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_ai_client: AsyncOpenAI | None = None


def get_ai_client() -> AsyncOpenAI:
    global _ai_client
    if _ai_client is None:
        _ai_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=httpx.Timeout(
                timeout=settings.DEEPSEEK_TIMEOUT,
                connect=settings.DEEPSEEK_CONNECT_TIMEOUT,
            ),
        )
    return _ai_client


async def content_diff(new_text: str, library_texts: dict[str, str]) -> dict:
    client = get_ai_client()

    existing_summary = ""
    for filename, text in library_texts.items():
        existing_summary += f"\n--- 文档: {filename} ---\n{text[:2000]}\n"

    prompt = f"""你是一个文档内容分析专家。请对比新文档与已有文档库的内容，找出差异。

新文档内容：
{new_text[:8000]}

已有文档库内容摘要：
{existing_summary or "（空文档库）"}

请严格按照以下JSON格式输出分析结果，不要添加任何其他文字：
{{
  "new": ["新文档中的全新段落1", "新文档中的全新段落2"],
  "conflict": [
    {{
      "new": "新文档中与旧文档冲突的内容",
      "old_doc_name": "冲突的旧文档文件名",
      "old": "旧文档中的对应内容"
    }}
  ]
}}

注意：
- "new" 数组只包含在新文档中出现但在已有文档库中完全不存在的内容。
  去除所有Markdown标记（#、**、[]等），只保留纯文本。
- "conflict" 数组记录新文档与旧文档讲相同主题但内容不同的部分。
  每个冲突记录需要指明旧文档的文件名和具体冲突内容。
- 如果新文档与已有文档内容完全一致，请返回空数组。
- 只输出JSON，不要添加解释或说明。"""

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )
        text = response.choices[0].message.content or "{}"
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("\n", 1)[0] if text.endswith("```") else text
            if text.startswith("json"):
                text = text.split("\n", 1)[1]
        return json.loads(text)
    except Exception as e:
        logger.error("content_diff failed: %s", str(e))
        raise


async def grammar_rewrite(text: str) -> str:
    client = get_ai_client()
    prompt = settings.GRAMMAR_REWRITE_PROMPT + "\n\n" + text

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=8192,
        )
        return (response.choices[0].message.content or text).strip()
    except Exception as e:
        logger.error("grammar_rewrite failed: %s", str(e))
        raise


async def style_rewrite(text: str, style_prompt: str) -> str:
    client = get_ai_client()
    prompt = f"{style_prompt}\n\n{text}"

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=8192,
        )
        return (response.choices[0].message.content or text).strip()
    except Exception as e:
        logger.error("style_rewrite failed: %s", str(e))
        raise

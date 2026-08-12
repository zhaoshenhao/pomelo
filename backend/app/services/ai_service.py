import json
import logging

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.prompts_config import get_prompts

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
        return _parse_llm_json(text)
    except Exception as e:
        logger.error("content_diff failed: %s", str(e))
        raise


async def grammar_rewrite(text: str) -> str:
    client = get_ai_client()
    prompts = get_prompts()
    prompt = prompts["grammar_rewrite_prompt"] + "\n\n" + text

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


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) >= 2:
            lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
        if lines and lines[0].strip() == "json":
            lines = lines[1:]
        text = "\n".join(lines)
    return text


def _escape_raw_newlines_in_strings(text: str) -> str:
    """Escape literal newlines/control chars inside JSON string values.

    LLMs often emit JSON with raw newlines inside string values, which makes
    json.loads fail with "Unterminated string". This scans the text tracking
    string boundaries (and escaped quotes/backslashes) and escapes raw control
    characters inside strings.
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        else:
            if ch == '"':
                out.append(ch)
                in_string = True
            else:
                out.append(ch)
    return "".join(out)


def _parse_llm_json(raw: str) -> dict:
    text = _strip_json_fence(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_escape_raw_newlines_in_strings(text))
    except json.JSONDecodeError as e:
        logger.error(
            "LLM JSON parse failed: %s | raw(500): %s",
            str(e), text[:500].replace("\n", "\\n"),
        )
        raise


async def _generate_json(client, prompt: str, *, max_tokens: int, temperature: float) -> dict:
    last_error: Exception | None = None
    use_json_mode = settings.AI_JSON_MODE
    for attempt in range(3):
        kwargs = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = await client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content or "{}"
            return _parse_llm_json(raw)
        except Exception as e:
            last_error = e
            if use_json_mode and "response_format" in str(e).lower():
                use_json_mode = False
            logger.warning("AI JSON generation attempt %d/3 failed: %s", attempt + 1, str(e))
    logger.error("AI JSON generation failed after 3 attempts: %s", str(last_error))
    raise RuntimeError("AI 调用失败，请稍后再试")


async def generate_study_material(docs: dict[str, str], style_prompt: str) -> dict:
    client = get_ai_client()

    doc_texts = ""
    doc_max = settings.AI_DOC_MAX_CHARS
    total_max = settings.AI_TOTAL_MAX_CHARS
    for filename, content in docs.items():
        doc_texts += f"\n--- 文档: {filename} ---\n{content[:doc_max]}\n"
    total_len = len(doc_texts)
    if total_len > total_max:
        doc_texts = doc_texts[:total_max]

    prompts = get_prompts()
    prompt = (
        prompts["study_material_prompt"]
        + "\n\n"
        + f"以下为选定的风格要求：\n{style_prompt}\n\n"
        + "以下为学习资料的参考文档：\n"
        + doc_texts
    )

    try:
        return await _generate_json(
            client, prompt,
            max_tokens=settings.AI_STUDY_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE,
        )
    except Exception as e:
        logger.error("generate_study_material failed: %s", str(e))
        raise


async def generate_exam(docs: dict[str, str], style_prompt: str) -> dict:
    client = get_ai_client()

    doc_texts = ""
    doc_max = settings.AI_DOC_MAX_CHARS
    total_max = settings.AI_TOTAL_MAX_CHARS
    for filename, content in docs.items():
        doc_texts += f"\n--- 文档: {filename} ---\n{content[:doc_max]}\n"
    total_len = len(doc_texts)
    if total_len > total_max:
        doc_texts = doc_texts[:total_max]

    prompts = get_prompts()
    prompt = (
        prompts["exam_prompt"]
        + "\n\n"
        + f"以下为选定的出题要求：\n{style_prompt}\n\n"
        + "以下为参考文档：\n"
        + doc_texts
    )

    try:
        return await _generate_json(
            client, prompt,
            max_tokens=settings.AI_QB_MAX_TOKENS,
            temperature=0.5,
        )
    except Exception as e:
        logger.error("generate_exam failed: %s", str(e))
        raise


async def evaluate_exam(questions: list[dict], correct_answers: dict, student_answers: list[dict]) -> str:
    client = get_ai_client()
    summary_lines = []
    for a in student_answers:
        qid = a.get("question_id", "")
        answered = str(a.get("answer", ""))
        expected = str(correct_answers.get(qid, ""))
        summary_lines.append(f"- Q{qid}: 学员答={answered}, 正确答案={expected}")
    prompt = (
        "你是一位教学分析师。请基于学员的答题情况给出简短的评价和学习建议。\n\n"
        + "\n".join(summary_lines)
        + "\n\n请用2-3句话给出评价和建议（中文）。"
    )
    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error("evaluate_exam failed: %s", str(e))
        return ""


async def summarize_exam(student_results: list[dict]) -> str:
    client = get_ai_client()
    summary = "\n".join([
        f"- 学员{r.get('student_id','?')}: 得分{r.get('score',0)}/{r.get('total',0)}, {'通过' if r.get('passed') else '未通过'}"
        for r in student_results[:20]
    ])
    prompt = (
        "你是一位教学分析师。请根据以下学员考试成绩，分析文档知识的整体覆盖情况和薄弱环节。\n\n"
        + summary
        + "\n\n请用3-5句话总结知识覆盖情况和改进建议（中文）。"
    )
    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error("summarize_exam failed: %s", str(e))
        return ""

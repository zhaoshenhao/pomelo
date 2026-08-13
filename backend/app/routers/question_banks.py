import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_teacher_or_admin
from app.models.ai_prompt import AIPrompt
from app.models.document import Document, DocumentLibrary
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.question_bank import (
    QuestionBankGenerateRequest,
    QuestionBankListItem,
    QuestionBankListResponse,
    QuestionBankResponse,
    QuestionBankUpdateRequest,
)
from app.services.ai_service import generate_exam
from app.services.file_service import (
    delete_qb_dir,
    read_qb_file,
    save_qb_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/question-banks", tags=["question_banks"])

VALID_TYPES = {"fill", "true_false", "single", "multiple", "match"}


def _is_valid_question(q: dict) -> bool:
    qtype = q.get("type", "")
    if qtype not in VALID_TYPES:
        return False
    if not q.get("question"):
        return False
    if qtype == "single" and "answer" not in q:
        return False
    if qtype == "multiple" and "answers" not in q:
        return False
    if qtype == "fill" and "answer" not in q:
        return False
    if qtype == "true_false" and "answer" not in q:
        return False
    if qtype == "match" and "matches" not in q:
        return False
    return True


def _filter_valid_questions(questions: list[dict]) -> list[dict]:
    if not questions:
        return []
    valid: list[dict] = []
    dropped = 0
    for q in questions:
        if _is_valid_question(q):
            valid.append(q)
        else:
            qtype = q.get("type", "?")
            logger.warning("Dropping invalid question %s: type=%s", q.get("id", "?"), qtype)
            dropped += 1
    if dropped:
        logger.warning("_filter_valid_questions: dropped %d invalid questions, kept %d", dropped, len(valid))
    return valid


def _extract_prefix(s: str, default_idx: int, alphabet: str) -> str:
    s = str(s).strip()
    if s and s[0].upper() in set(alphabet):
        return s[0].upper()
    return alphabet[default_idx] if default_idx < len(alphabet) else str(default_idx)


def _normalize_match(q: dict):
    left = q.get("left", [])
    right = q.get("right", [])
    raw = q.get("matches", {})
    if not left or not right or not raw:
        return
    left_map: dict[str, str] = {}
    for i, item in enumerate(left):
        key = _extract_prefix(item, i, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        left_map[key] = str(item)
    right_map: dict[str, str] = {}
    for i, item in enumerate(right):
        val = _extract_prefix(item, i, "123456789")
        right_map[val] = str(item)
    new_matches: dict[str, str] = {}
    for k, v in raw.items():
        lk = str(k).strip()
        rv = str(v).strip()
        litem = left_map.get(lk, lk)
        if litem not in left:
            continue
        ritem = right_map.get(rv, rv)
        new_matches[litem] = ritem
    if new_matches:
        q["matches"] = new_matches


def _normalize_questions(questions: list[dict]):
    for q in questions:
        if q.get("type") == "match":
            _normalize_match(q)


async def _resolve_names(
    session: AsyncSession,
    library_ids: set[int],
    user_ids: set[int],
) -> tuple[dict[int, str], dict[int, str]]:
    lib_map: dict[int, str] = {}
    user_map: dict[int, str] = {}
    if library_ids:
        libs = await session.execute(
            select(DocumentLibrary.id, DocumentLibrary.name).where(DocumentLibrary.id.in_(library_ids))
        )
        for lid, lname in libs:
            lib_map[lid] = lname
    if user_ids:
        usrs = await session.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        for uid, uname in usrs:
            user_map[uid] = uname
    return lib_map, user_map


_jobs: dict[str, dict] = {}
_background_tasks: set[asyncio.Task] = set()


async def _run_generation(
    job_id: str, name: str, description: str, library_id: int,
    document_names_str: str, prompt_id: int, prompt_text: str,
    doc_contents: dict[str, str], user_id: int,
):
    logger.info("_run_generation started job %s", job_id)
    try:
        from app import database as _db
        logger.info("_run_generation using session: %s", type(_db.async_session).__name__)
        async with _db.async_session() as s:
            qb = QuestionBank(
                name=name, description=description,
                library_id=library_id, document_names=document_names_str,
                prompt_id=prompt_id, prompt_text=prompt_text,
                created_by=user_id,
            )
            s.add(qb)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                _jobs[job_id] = {"status": "failed", "error": "题库名称已存在"}
                return

            ai_data = await generate_exam(doc_contents, prompt_text)
            questions = ai_data.get("questions", [])
            valid = _filter_valid_questions(questions)
            if not valid:
                await s.delete(qb)
                await s.commit()
                _jobs[job_id] = {"status": "failed", "error": "AI 返回的题目格式均不正确，请重试"}
                return

            _normalize_questions(valid)
            TYPE_ORDER = {"single": 0, "multiple": 1, "true_false": 2, "fill": 3, "match": 4}
            valid.sort(key=lambda q: TYPE_ORDER.get(q.get("type", ""), 99))
            for i, q in enumerate(valid, 1):
                q["id"] = f"q{i}"
            type_counts: dict[str, int] = {}
            for q in valid:
                t = q.get("type", "?")
                type_counts[t] = type_counts.get(t, 0) + 1
            statistics = {"total": len(valid), "types": type_counts}

            save_qb_file(qb.id, "qb.json",
                         json.dumps({"id": qb.id, "name": qb.name, "description": qb.description,
                                     "prompt_text": qb.prompt_text,
                                     "statistics": statistics,
                                     "questions": valid}, ensure_ascii=False, indent=2))

            _jobs[job_id] = {"status": "done", "result": {"id": qb.id, "name": qb.name, "questions": len(valid)}}
    except Exception as e:
        logger.exception("Generation job %s failed", job_id)
        _jobs[job_id] = {"status": "failed", "error": str(e)}


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_question_bank(
    request: QuestionBankGenerateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == request.library_id)
    )).scalar_one_or_none()
    if lib is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    if request.document_names:
        docs = (await session.execute(
            select(Document).where(
                Document.library_id == request.library_id,
                Document.filename.in_(request.document_names),
            )
        )).scalars().all()
        found_names = {d.filename for d in docs}
        for name in request.document_names:
            if name not in found_names:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"文档「{name}」在该库中不存在")
    else:
        docs = (await session.execute(
            select(Document).where(Document.library_id == request.library_id)
        )).scalars().all()
        if not docs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档库中没有文档可供出题")

    prompt = (await session.execute(
        select(AIPrompt).where(AIPrompt.id == request.prompt_id, AIPrompt.prompt_type == "exam")
    )).scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷提示词不存在")

    existing = (await session.execute(
        select(QuestionBank).where(QuestionBank.name == request.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="题库名称已存在")

    doc_contents: dict[str, str] = {}
    for doc in docs:
        try:
            with open(doc.path, "r", encoding="utf-8") as f:
                doc_contents[doc.filename] = f.read()
        except OSError:
            continue

    if not doc_contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="所选文档均无法读取")

    doc_names_str = ",".join(request.document_names) if request.document_names else ",".join(d.filename for d in docs)

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    task = asyncio.create_task(_run_generation(
        job_id, request.name, request.description, request.library_id,
        doc_names_str, request.prompt_id, prompt.prompt,
        doc_contents, current_user.id,
    ))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info("Job %s created, background task scheduled", job_id)
    return success_response({"job_id": job_id}, "生成任务已启动")


@router.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return success_response(job)


def _qb_counts(qb_id: int) -> tuple[int, dict[str, int]]:
    try:
        content = read_qb_file(qb_id, "qb.json")
        data = json.loads(content)
        stats = data.get("statistics", {})
        question_count = stats.get("total", 0)
        type_counts = stats.get("types", {})
        return question_count, type_counts
    except (OSError, json.JSONDecodeError):
        return 0, {}


@router.get("")
async def list_question_banks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    base = select(QuestionBank)
    if search:
        base = base.where(QuestionBank.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    rows = await session.execute(base.order_by(QuestionBank.id.desc()).offset(offset).limit(page_size))
    qbs = rows.scalars().all()

    lib_ids = {q.library_id for q in qbs}
    user_ids = {q.created_by for q in qbs}
    lib_map, user_map = await _resolve_names(session, lib_ids, user_ids)

    items = []
    for q in qbs:
        count, type_counts = _qb_counts(q.id)
        items.append(QuestionBankListItem(
            id=q.id, name=q.name, description=q.description,
            library_id=q.library_id, library_name=lib_map.get(q.library_id, ""),
            document_names=q.document_names,
            creator_name=user_map.get(q.created_by, ""),
            created_at=q.created_at, updated_at=q.updated_at,
            disabled=q.disabled,
            question_count=count,
            type_counts=type_counts,
        ))
    return success_response(QuestionBankListResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/{qb_id}")
async def get_question_bank(
    qb_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    qb = (await session.execute(select(QuestionBank).where(QuestionBank.id == qb_id))).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")
    lib = (await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == qb.library_id))).scalar_one_or_none()
    user = (await session.execute(select(User).where(User.id == qb.created_by))).scalar_one_or_none()
    return success_response(QuestionBankResponse(
        id=qb.id, name=qb.name, description=qb.description,
        library_id=qb.library_id, library_name=lib.name if lib else "",
        document_names=qb.document_names, prompt_id=qb.prompt_id,
        created_by=qb.created_by, creator_name=user.username if user else "",
        created_at=qb.created_at, updated_at=qb.updated_at,
    ))


@router.get("/{qb_id}/paper")
async def get_question_bank_paper(
    qb_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    qb = (await session.execute(select(QuestionBank).where(QuestionBank.id == qb_id))).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")
    try:
        content = read_qb_file(qb.id, "qb.json")
        data = json.loads(content)
        if "prompt_text" not in data and qb.prompt_text:
            data["prompt_text"] = qb.prompt_text
        return success_response(data)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库文件不存在")


@router.put("/{qb_id}")
async def update_question_bank(
    qb_id: int,
    request: QuestionBankUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    qb = (await session.execute(select(QuestionBank).where(QuestionBank.id == qb_id))).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")
    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="名称不能为空")
        existing = (await session.execute(
            select(QuestionBank).where(QuestionBank.name == request.name, QuestionBank.id != qb_id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="题库名称已存在")
        qb.name = request.name
    if request.description is not None:
        qb.description = request.description
    if request.disabled is not None:
        qb.disabled = request.disabled
    await session.commit()
    await session.refresh(qb)
    return success_response(None, "更新成功")


@router.delete("/{qb_id}")
async def delete_question_bank(
    qb_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    qb = (await session.execute(select(QuestionBank).where(QuestionBank.id == qb_id))).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")
    delete_qb_dir(qb.id)
    await session.delete(qb)
    await session.commit()
    return success_response(None, "删除成功")

import json
import logging
import os
import random
from datetime import datetime as _dt
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_student, require_teacher_or_admin
from app.models.exam import Exam, ExamAssignment, ExamBatch
from app.models.question_bank import QuestionBank
from app.models.student_tag import student_tag_links
from app.models.user import User, UserRole
from app.schemas.common import success_response
from app.schemas.exam import (
    AssignmentResponse,
    BatchStudentAddRequest as ExamBatchStudentAddRequest,
    CrossCell,
    CrossTableRow,
    ExamBatchCreateRequest,
    ExamBatchDetailResponse,
    ExamBatchListResponse,
    ExamBatchResponse,
    ExamBatchUpdateRequest,
    ExamGenerateRequest,
    ExamGenerateValidateRequest,
    ExamGenerateValidateResponse,
    ExamListItem,
    ExamListResponse,
    ExamResponse,
    ExamSubmitRequest,
    ExamSubmitResponse,
    ExamTakeResponse,
    ExamUpdateRequest,
    TypeScoreRow,
)
from app.services.ai_service import evaluate_exam, summarize_exam
from app.services.exam_service import grade_exam, summarize_results
from app.services.file_service import (
    get_exam_batch_dir,
    read_exam_batch_file,
    read_exam_file,
    read_qb_file,
    save_exam_batch_file,
    save_exam_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exams", tags=["exams"])


async def _resolve_user_names(session: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    user_map: dict[int, str] = {}
    if user_ids:
        usrs = await session.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        for uid, uname in usrs:
            user_map[uid] = uname
    return user_map


def _load_qb(qb_id: int) -> dict | None:
    try:
        content = read_qb_file(qb_id, "qb.json")
        return json.loads(content)
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_bank_counts(banks: list, total_questions: int) -> tuple[dict[int, int], str | None]:
    if not banks:
        return {}, "至少选择一个题库"
    n = len(banks)
    if n == 1:
        banks[0].percentage = 100
    else:
        filled = sum(b.percentage for b in banks if b.percentage > 0)
        if filled > 100:
            return {}, "各题库占比总和不能超过 100%"
        blanks = [b for b in banks if b.percentage <= 0]
        if blanks:
            remaining = 100 - filled
            per = remaining // len(blanks)
            extra = remaining % len(blanks)
            for i, b in enumerate(blanks):
                b.percentage = per + (1 if i < extra else 0)
    raw = {b.qb_id: total_questions * b.percentage / 100.0 for b in banks}
    base = {qid: int(v) for qid, v in raw.items()}
    remainder = {qid: v - int(v) for qid, v in raw.items()}
    extra_count = total_questions - sum(base.values())
    for qid in sorted(remainder, key=lambda k: -remainder[k])[:extra_count]:
        base[qid] += 1
    return base, None


@router.post("/generate/validate")
async def validate_generation(
    request: ExamGenerateValidateRequest,
    _current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    errors: list[str] = []
    if not request.name.strip():
        errors.append("名称不能为空")
    if len(request.banks) == 0:
        errors.append("至少选择一个题库")
    if len(request.types) == 0:
        errors.append("至少选择一个题型")

    if errors:
        return success_response(ExamGenerateValidateResponse(
            valid=False, errors=errors, total_score=0, total_questions=0,
            duration_minutes=request.duration_minutes, pass_score=request.pass_score,
        ))

    qb_names: dict[int, str] = {}
    qb_available: dict[int, dict[str, int]] = {}
    qb_questions: dict[int, list[dict]] = {}

    for b in request.banks:
        qb_row = (await session.execute(
            select(QuestionBank).where(QuestionBank.id == b.qb_id)
        )).scalar_one_or_none()
        if qb_row is None:
            errors.append(f"题库 ID {b.qb_id} 不存在")
            continue
        if qb_row.disabled:
            errors.append(f"题库「{qb_row.name}」已被禁止，无法用于生成试卷")
            continue
        qb_names[b.qb_id] = qb_row.name
        dump = _load_qb(b.qb_id)
        if dump is None:
            errors.append(f"题库「{qb_row.name}」无题目数据")
            continue
        questions = dump.get("questions", [])
        qb_questions[b.qb_id] = questions
        counts: dict[str, int] = {}
        for q in questions:
            t = q.get("type", "")
            counts[t] = counts.get(t, 0) + 1
        qb_available[b.qb_id] = counts

    if errors:
        return success_response(ExamGenerateValidateResponse(
            valid=False, errors=errors, total_score=0, total_questions=0,
            duration_minutes=request.duration_minutes, pass_score=request.pass_score,
        ))

    total_questions = sum(t.count for t in request.types)
    total_score = sum(t.count * t.score for t in request.types)
    if total_score != 100:
        errors.append(f"总分必须为 100，当前为 {total_score} 分")

    counts, pct_error = _resolve_bank_counts(request.banks, total_questions)
    if pct_error:
        errors.append(pct_error)
        return success_response(ExamGenerateValidateResponse(
            valid=False, errors=errors, total_score=total_score, total_questions=total_questions,
            duration_minutes=request.duration_minutes, pass_score=request.pass_score,
        ))

    for b in request.banks:
        c = counts.get(b.qb_id, 0)
        if c <= 0:
            continue
        avail = sum(qb_available[b.qb_id].values())
        if c > avail:
            errors.append(f"题库「{qb_names[b.qb_id]}」只有 {avail} 道题，不够抽取 {c} 道")

    if errors:
        return success_response(ExamGenerateValidateResponse(
            valid=False, errors=errors, total_score=total_score, total_questions=total_questions,
            duration_minutes=request.duration_minutes, pass_score=request.pass_score,
        ))

    bank_remaining = dict(counts)
    cross: dict[int, dict[str, int]] = {b.qb_id: {} for b in request.banks}
    alloc_errors: list[str] = []

    for t in request.types:
        need = t.count
        for b in request.banks:
            if need <= 0:
                break
            if bank_remaining[b.qb_id] <= 0:
                continue
            avail = qb_available[b.qb_id].get(t.type, 0) - cross[b.qb_id].get(t.type, 0)
            take = min(need, bank_remaining[b.qb_id], avail)
            if take > 0:
                cross[b.qb_id][t.type] = cross[b.qb_id].get(t.type, 0) + take
                bank_remaining[b.qb_id] -= take
                need -= take
        if need > 0:
            alloc_errors.append(f"题型「{t.type}」分配不足，缺少 {need} 道题")

    if alloc_errors:
        errors.extend(alloc_errors)

    cross_table: list[CrossTableRow] = []
    for b in request.banks:
        cells = [CrossCell(count=cross[b.qb_id].get(t.type, 0)) for t in request.types]
        row_total = sum(c.count for c in cells)
        cross_table.append(CrossTableRow(qb_id=b.qb_id, qb_name=qb_names.get(b.qb_id, ""), cells=cells, total=row_total))

    type_table: list[TypeScoreRow] = []
    for t in request.types:
        col_total = sum(cross[b.qb_id].get(t.type, 0) for b in request.banks)
        type_table.append(TypeScoreRow(per_score=t.score, count=col_total, total_score=col_total * t.score))

    return success_response(ExamGenerateValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        cross_table=cross_table,
        type_table=type_table,
        total_questions=total_questions,
        total_score=total_score,
        duration_minutes=request.duration_minutes,
        pass_score=request.pass_score,
    ))


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_exam(
    request: ExamGenerateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    existing = (await session.execute(
        select(Exam).where(Exam.name == request.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="试卷名称已存在")

    qb_questions: dict[int, list[dict]] = {}
    for b in request.banks:
        qb_row = (await session.execute(
            select(QuestionBank).where(QuestionBank.id == b.qb_id)
        )).scalar_one_or_none()
        if qb_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"题库 {b.qb_id} 不存在")
        if qb_row.disabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"题库「{qb_row.name}」已被禁止，无法用于生成试卷")
        dump = _load_qb(b.qb_id)
        if dump is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"题库 {b.qb_id} 不存在或无题目")
        qb_questions[b.qb_id] = dump.get("questions", [])

    total_questions = sum(t.count for t in request.types)
    counts, pct_error = _resolve_bank_counts(request.banks, total_questions)
    if pct_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pct_error)

    bank_remaining = dict(counts)

    drawn: list[dict] = []
    next_qid = 1

    for t in request.types:
        need = t.count
        for b in request.banks:
            if need <= 0:
                break
            if bank_remaining[b.qb_id] <= 0:
                continue
            pool = [q for q in qb_questions[b.qb_id] if q.get("type") == t.type]
            random.shuffle(pool)
            take = min(need, bank_remaining[b.qb_id], len(pool))
            for q in pool[:take]:
                q_copy = dict(q)
                q_copy["id"] = f"q{next_qid}"
                next_qid += 1
                drawn.append(q_copy)
            bank_remaining[b.qb_id] -= take
            need -= take
        if need > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"题型「{t.type}」题目不足")

    exam = Exam(
        name=request.name,
        description=request.description,
        duration_minutes=request.duration_minutes,
        pass_score=request.pass_score,
        created_by=current_user.id,
    )
    session.add(exam)
    await session.commit()
    await session.refresh(exam)

    try:
        save_exam_file(exam.id, "exam.json",
                       json.dumps({"id": exam.id, "name": exam.name, "description": exam.description,
                                   "duration_minutes": exam.duration_minutes, "pass_score": exam.pass_score,
                                   "questions": drawn}, ensure_ascii=False, indent=2))
    except Exception:
        await session.delete(exam)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="试卷文件写入失败")

    creator_name = current_user.username
    return success_response({
        "id": exam.id, "name": exam.name, "description": exam.description,
        "duration_minutes": exam.duration_minutes, "pass_score": exam.pass_score,
        "created_by": exam.created_by, "creator_name": creator_name,
        "created_at": exam.created_at.isoformat(), "updated_at": exam.updated_at.isoformat(),
        "questions": drawn,
    }, "生成成功")


@router.get("")
async def list_exams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    base = select(Exam)
    if search:
        base = base.where(Exam.name.ilike(f"%{search}%"))
    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    rows = await session.execute(base.order_by(Exam.id.desc()).offset(offset).limit(page_size))
    exams = rows.scalars().all()
    user_ids = {e.created_by for e in exams}
    user_map = await _resolve_user_names(session, user_ids)
    items = [
        ExamListItem(
            id=e.id, name=e.name, description=e.description,
            duration_minutes=e.duration_minutes, pass_score=e.pass_score,
            creator_name=user_map.get(e.created_by, ""),
            created_at=e.created_at, updated_at=e.updated_at,
        )
        for e in exams
    ]
    return success_response(ExamListResponse(items=items, total=total, page=page, page_size=page_size))


# ─── student ───

@router.get("/my")
async def my_exams(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    now = _dt.now()
    assignments = (await session.execute(
        select(ExamAssignment).where(ExamAssignment.student_id == current_user.id)
    )).scalars().all()

    upcoming: list[dict] = []
    in_progress: list[dict] = []
    completed: list[dict] = []
    expired_unfinished: list[dict] = []

    batch_ids = {a.batch_id for a in assignments}
    batch_map: dict[int, ExamBatch] = {}
    if batch_ids:
        batches = (await session.execute(
            select(ExamBatch).where(ExamBatch.id.in_(batch_ids))
        )).scalars().all()
        batch_map = {b.id: b for b in batches}

    exam_ids = {a.exam_id for a in assignments}
    exams = (await session.execute(select(Exam).where(Exam.id.in_(exam_ids)))).scalars().all()
    exam_map = {e.id: e for e in exams}

    for a in assignments:
        e = exam_map.get(a.exam_id)
        if e is None:
            continue
        batch = batch_map.get(a.batch_id)
        if batch and batch.disabled:
            continue

        start = batch.start_time if batch else None
        end = batch.end_time if batch else None
        dur = batch.duration_minutes if batch and batch.duration_minutes is not None else e.duration_minutes
        pscore = batch.pass_score if batch and batch.pass_score is not None else e.pass_score

        item = {
            "assignment_id": a.id, "exam_id": a.exam_id, "batch_id": a.batch_id,
            "name": batch.name or e.name if batch else e.name,
            "description": batch.description or e.description,
            "duration_minutes": dur, "pass_score": pscore,
            "start_time": start.isoformat() if start else None,
            "end_time": end.isoformat() if end else None,
            "status": a.status,
            "score": a.score, "passed": a.passed,
        }

        if a.status == "completed":
            completed.append(item)
        elif end and end < now:
            item["score"] = 0
            item["passed"] = False
            expired_unfinished.append(item)
        elif start and start > now:
            upcoming.append(item)
        else:
            in_progress.append(item)

    return success_response({
        "upcoming": upcoming,
        "in_progress": in_progress,
        "completed": completed,
        "expired": expired_unfinished,
    })


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    user = (await session.execute(select(User).where(User.id == exam.created_by))).scalar_one_or_none()
    return success_response(ExamResponse(
        id=exam.id, name=exam.name, description=exam.description,
        duration_minutes=exam.duration_minutes, pass_score=exam.pass_score,
        created_by=exam.created_by, creator_name=user.username if user else "",
        created_at=exam.created_at, updated_at=exam.updated_at,
    ))



@router.get("/{exam_id}/paper")
async def get_exam_paper(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    try:
        content = read_exam_file(exam.id, "exam.json")
        return success_response(json.loads(content))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷文件不存在")


@router.put("/{exam_id}")
async def update_exam(
    exam_id: int,
    request: ExamUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="名称不能为空")
        existing = (await session.execute(
            select(Exam).where(Exam.name == request.name, Exam.id != exam_id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="试卷名称已存在")
        exam.name = request.name
    if request.description is not None:
        exam.description = request.description
    if request.duration_minutes is not None:
        exam.duration_minutes = request.duration_minutes
    if request.pass_score is not None:
        exam.pass_score = request.pass_score
    await session.commit()
    await session.refresh(exam)
    return success_response(None, "更新成功")


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    from sqlalchemy import delete as sa_delete
    await session.execute(sa_delete(ExamAssignment).where(ExamAssignment.exam_id == exam_id))
    await session.execute(sa_delete(ExamBatch).where(ExamBatch.exam_id == exam_id))
    from app.services.file_service import delete_exam_dir
    delete_exam_dir(exam.id)
    await session.delete(exam)
    await session.commit()
    return success_response(None, "删除成功")


# ─── batches ───

@router.get("/{exam_id}/batches")
async def list_batches(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    batches = (await session.execute(
        select(ExamBatch).where(ExamBatch.exam_id == exam_id).order_by(ExamBatch.id)
    )).scalars().all()
    arranger_ids = {b.arranged_by for b in batches}
    user_map = await _resolve_user_names(session, arranger_ids)

    # compute per-batch stats
    all_assignments = (await session.execute(
        select(ExamAssignment).where(ExamAssignment.exam_id == exam_id)
    )).scalars().all()
    batch_stats: dict[int, dict] = {}
    for a in all_assignments:
        s = batch_stats.setdefault(a.batch_id, {"arranged": 0, "completed": 0, "scores": []})
        s["arranged"] += 1
        if a.status == "completed":
            s["completed"] += 1
            if a.score is not None:
                s["scores"].append(a.score)
            if a.passed:
                s.setdefault("passed", 0)
                s["passed"] += 1

    items = [
        ExamBatchResponse(
            id=b.id, exam_id=b.exam_id, arranged_by=b.arranged_by,
            arranged_by_name=user_map.get(b.arranged_by, ""),
            name=b.name, description=b.description,
            start_time=b.start_time, end_time=b.end_time,
            duration_minutes=b.duration_minutes, pass_score=b.pass_score,
            disabled=b.disabled, created_at=b.created_at, updated_at=b.updated_at,
            arranged_count=batch_stats.get(b.id, {}).get("arranged", 0),
            completed_count=batch_stats.get(b.id, {}).get("completed", 0),
            pass_rate=round(batch_stats.get(b.id, {}).get("passed", 0) / max(bs.get("completed", 1), 0) * 100, 1) if (bs := batch_stats.get(b.id, {})) and bs.get("completed", 0) else None,
            average_score=round(sum(bs2["scores"]) / len(bs2["scores"]), 1) if (bs2 := batch_stats.get(b.id)) and bs2.get("completed", 0) else None,
        )
        for b in batches
    ]
    return success_response(ExamBatchListResponse(batches=items))


@router.post("/{exam_id}/batches", status_code=status.HTTP_201_CREATED)
async def create_batch(
    exam_id: int,
    request: ExamBatchCreateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    # resolve students from tags + explicit list
    student_set: set[int] = set(request.student_ids)
    if request.tag_ids:
        tagged = (await session.execute(
            select(student_tag_links.c.user_id).where(
                student_tag_links.c.tag_id.in_(request.tag_ids)
            )
        )).scalars().all()
        student_set.update(tagged)
        student_set = {uid for uid in student_set if uid}

    if not student_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未选择任何学员")

    # verify all are students
    users = (await session.execute(
        select(User).where(User.id.in_(list(student_set)))
    )).scalars().all()
    user_map = {u.id: u for u in users}
    non_students = [uid for uid in student_set if uid not in user_map or user_map[uid].role != UserRole.STUDENT]
    if non_students:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="选中的用户包含非学员")

    # auto-exclude completed within N days
    if request.exclude_completed_days > 0:
        since = _dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = since - timedelta(days=request.exclude_completed_days)
        completed = (await session.execute(
            select(ExamAssignment).where(
                ExamAssignment.exam_id == exam_id,
                ExamAssignment.student_id.in_(list(student_set)),
                ExamAssignment.status == "completed",
                ExamAssignment.passed,
                ExamAssignment.completed_at >= cutoff,
            )
        )).scalars().all()
        exclude_ids = {a.student_id for a in completed}
        student_set -= exclude_ids

    if not student_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自动排除后无可用学员")

    batch = ExamBatch(
        exam_id=exam_id, arranged_by=current_user.id,
        name=request.name or exam.name,
        description=request.description or exam.description,
        start_time=request.start_time, end_time=request.end_time,
        duration_minutes=request.duration_minutes or exam.duration_minutes,
        pass_score=request.pass_score or exam.pass_score,
    )
    session.add(batch)
    await session.flush()

    # filter out students already in another assignment for this exam? No — unique is by batch_id, student_id
    added = 0
    for sid in sorted(student_set):
        session.add(ExamAssignment(
            exam_id=exam_id, student_id=sid, batch_id=batch.id, status="assigned",
        ))
        added += 1

    await session.commit()
    get_exam_batch_dir(exam_id, batch.id)
    return success_response({"id": batch.id}, f"已安排 {added} 名学员")


@router.get("/{exam_id}/batches/{batch_id}")
async def get_batch(
    exam_id: int,
    batch_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    arranger = (await session.execute(select(User.username).where(User.id == batch.arranged_by))).scalar() or ""
    batch_students = (await session.execute(
        select(ExamAssignment).where(ExamAssignment.batch_id == batch_id)
    )).scalars().all()
    sid_set = {a.student_id for a in batch_students}
    user_map = await _resolve_user_names(session, sid_set)

    students = []
    for a in batch_students:
        correct = 0
        total = 0
        if a.status == "completed":
            try:
                content = read_exam_batch_file(exam_id, batch_id, f"{a.student_id}.json")
                sr = json.loads(content)
                correct = sr.get("correct", 0)
                total = sr.get("total", 0)
            except (OSError, json.JSONDecodeError):
                pass
        students.append(
            AssignmentResponse(
                id=a.id, exam_id=a.exam_id, student_id=a.student_id,
                student_name=user_map.get(a.student_id, ""),
                batch_id=a.batch_id, status=a.status,
                score=a.score, passed=a.passed, correct=correct, total=total, completed_at=a.completed_at,
            )
        )
    return success_response(ExamBatchDetailResponse(
        id=batch.id, exam_id=batch.exam_id, arranged_by=batch.arranged_by,
        arranged_by_name=arranger,
        name=batch.name, description=batch.description,
        start_time=batch.start_time, end_time=batch.end_time,
        duration_minutes=batch.duration_minutes, pass_score=batch.pass_score,
        disabled=batch.disabled, created_at=batch.created_at, students=students,
    ))


@router.put("/{exam_id}/batches/{batch_id}")
async def update_batch(
    exam_id: int,
    batch_id: int,
    request: ExamBatchUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    if request.name is not None:
        batch.name = request.name
    if request.description is not None:
        batch.description = request.description
    if request.duration_minutes is not None:
        batch.duration_minutes = request.duration_minutes
    if request.pass_score is not None:
        batch.pass_score = request.pass_score
    if request.disabled is not None:
        batch.disabled = request.disabled
    await session.commit()
    return success_response(None, "批次已更新")


@router.delete("/{exam_id}/batches/{batch_id}")
async def delete_batch(
    exam_id: int,
    batch_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    completed = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.batch_id == batch_id, ExamAssignment.status == "completed"
        )
    )).scalars().all()
    if completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="批次中包含已完成考试的学员，不能删除")
    from sqlalchemy import delete as sa_delete
    await session.execute(sa_delete(ExamAssignment).where(ExamAssignment.batch_id == batch_id))
    await session.delete(batch)
    await session.commit()
    return success_response(None, "批次已删除")


@router.post("/{exam_id}/batches/{batch_id}/students", status_code=status.HTTP_201_CREATED)
async def add_student_to_batch(
    exam_id: int,
    batch_id: int,
    request: ExamBatchStudentAddRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    user = (await session.execute(select(User).where(User.id == request.student_id))).scalar_one_or_none()
    if user is None or user.role != UserRole.STUDENT or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的学员")

    existing = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.batch_id == batch_id,
            ExamAssignment.student_id == request.student_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该学员已在本批次中")

    assignment = ExamAssignment(
        exam_id=exam_id, student_id=request.student_id, batch_id=batch_id, status="assigned",
    )
    session.add(assignment)
    await session.commit()
    return success_response(None, "学员已添加")


@router.delete("/{exam_id}/batches/{batch_id}/students/{student_id}")
async def remove_student_from_batch(
    exam_id: int,
    batch_id: int,
    student_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    assignment = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.batch_id == batch_id,
            ExamAssignment.student_id == student_id,
        )
    )).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该学员的安排记录")

    if assignment.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已完成考试的学员不能移除")

    await session.delete(assignment)
    await session.commit()

    # cleanup result file if exists
    import os
    rpath = os.path.join(get_exam_batch_dir(exam_id, batch_id), f"{student_id}.json")
    try:
        os.remove(rpath)
    except OSError:
        pass

    return success_response(None, "学员已移除")


@router.get("/{exam_id}/batches/{batch_id}/students/{student_id}")
async def get_student_result(
    exam_id: int,
    batch_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == batch_id, ExamBatch.exam_id == exam_id)
    )).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    assignment = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.batch_id == batch_id,
            ExamAssignment.student_id == student_id,
        )
    )).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该学员的安排记录")

    try:
        content = read_exam_batch_file(exam_id, batch_id, f"{student_id}.json")
        return success_response(json.loads(content))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学员答卷不存在")


# ─── results ───

@router.get("/{exam_id}/batches/{batch_id}/result")
async def get_batch_result(
    exam_id: int,
    batch_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        content = read_exam_batch_file(exam_id, batch_id, "result.json")
        return success_response(json.loads(content))
    except (OSError, json.JSONDecodeError):
        return success_response({
            "total_students": 0, "average_score": 0, "pass_rate": 0,
            "per_question_accuracy": [], "knowledge_coverage": "暂无汇总数据",
        })


@router.post("/{exam_id}/batches/{batch_id}/result/regenerate")
async def regenerate_batch_result(
    exam_id: int,
    batch_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        paper = json.loads(read_exam_file(exam_id, "exam.json"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="无法读取试卷")
    questions = paper.get("questions", [])

    student_results = []
    batch_dir = get_exam_batch_dir(exam_id, batch_id)
    if os.path.isdir(batch_dir):
        for fn in os.listdir(batch_dir):
            if fn == "result.json" or not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(batch_dir, fn), "r", encoding="utf-8") as f:
                    sr = json.load(f)
                if "results" in sr:
                    student_results.append(sr)
            except (OSError, json.JSONDecodeError):
                pass

    summary = summarize_results(student_results, questions)
    try:
        knowledge = await summarize_exam(student_results)
    except Exception:
        knowledge = "知识覆盖率分析暂不可用"
    summary["knowledge_coverage"] = knowledge

    save_exam_batch_file(exam_id, batch_id, "result.json",
                          json.dumps(summary, ensure_ascii=False, indent=2))
    return success_response(summary, "汇总完成")


@router.get("/{exam_id}/results")
async def get_results(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        content = read_exam_file(exam_id, "result.json")
        return success_response(json.loads(content))
    except (OSError, json.JSONDecodeError):
        return success_response({
            "total_students": 0, "average_score": 0, "pass_rate": 0,
            "per_question_accuracy": [], "knowledge_coverage": "暂无汇总数据",
        })


@router.post("/{exam_id}/results/regenerate")
async def regenerate_results(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        paper = json.loads(read_exam_file(exam_id, "exam.json"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="无法读取试卷")
    questions = paper.get("questions", [])

    # aggregate from all batch student result files
    all_results: list[dict] = []
    batches_dir = os.path.dirname(get_exam_batch_dir(exam_id, 0))
    if os.path.isdir(batches_dir):
        for bd in os.listdir(batches_dir):
            sdir = os.path.join(batches_dir, bd)
            if os.path.isdir(sdir):
                for fn in os.listdir(sdir):
                    if fn == "result.json" or not fn.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(sdir, fn), "r", encoding="utf-8") as f:
                            sr = json.load(f)
                        if "results" in sr:
                            all_results.append(sr)
                    except (OSError, json.JSONDecodeError):
                        pass

    summary = summarize_results(all_results, questions)
    try:
        knowledge = await summarize_exam(all_results)
    except Exception:
        knowledge = "知识覆盖率分析暂不可用"
    summary["knowledge_coverage"] = knowledge

    save_exam_file(exam_id, "result.json",
                   json.dumps(summary, ensure_ascii=False, indent=2))
    return success_response(summary, "汇总完成")


@router.get("/{exam_id}/results/export")
async def export_results_pdf(
    exam_id: int,
    batch_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    try:
        paper = json.loads(read_exam_file(exam_id, "exam.json"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷文件不存在")
    total_questions = len(paper.get("questions", []))

    query = select(ExamAssignment).where(ExamAssignment.exam_id == exam_id)
    if batch_id is not None:
        query = query.where(ExamAssignment.batch_id == batch_id)
    assignments = (await session.execute(query)).scalars().all()

    batch_ids = {a.batch_id for a in assignments}
    batch_map: dict[int, ExamBatch] = {}
    if batch_ids:
        batches = (await session.execute(
            select(ExamBatch).where(ExamBatch.id.in_(batch_ids))
        )).scalars().all()
        batch_map = {b.id: b for b in batches}

    user_ids = {a.student_id for a in assignments}
    user_map = await _resolve_user_names(session, user_ids)

    now = _dt.now()
    rows: list[dict] = []
    total_arranged = 0
    completed_count = 0
    passed_count = 0
    completed_scores: list[float] = []
    for a in assignments:
        total_arranged += 1
        name = user_map.get(a.student_id, str(a.student_id))
        batch = batch_map.get(a.batch_id)
        expired = bool(batch and batch.end_time and batch.end_time < now)

        if a.status == "completed":
            score_val = a.score or 0
            completed_count += 1
            completed_scores.append(score_val)
            if a.passed:
                passed_count += 1
            correct = 0
            total = total_questions
            try:
                sr = json.loads(read_exam_batch_file(exam_id, a.batch_id, f"{a.student_id}.json"))
                correct = sr.get("correct", 0)
                total = sr.get("total", total_questions)
            except (OSError, json.JSONDecodeError):
                pass
            status_str = "通过" if a.passed else "未通过"
        elif expired:
            score_val = 0
            correct = 0
            total = total_questions
            status_str = "未通过"
        else:
            score_val = "-"
            correct = "-"
            total = total_questions
            status_str = "未考试"

        rows.append({"name": name, "score": score_val, "correct": correct, "total": total, "status": status_str})

    # compute per-type question counts
    type_labels = {"single": "单选", "multiple": "多选", "true_false": "对错", "fill": "填空", "match": "匹配"}
    type_counts: dict[str, int] = {}
    for q in paper.get("questions", []):
        t = q.get("type", "")
        type_counts[t] = type_counts.get(t, 0) + 1
    type_str = "  ".join(f"{type_labels.get(t, t)}:{c}" for t, c in type_counts.items() if c) or "-"

    # compute time range
    time_range = "-"
    if batch_id and batch_map.get(batch_id):
        b = batch_map[batch_id]
        time_range = f"{b.start_time.strftime('%Y-%m-%d %H:%M') if b.start_time else '-'} ~ {b.end_time.strftime('%Y-%m-%d %H:%M') if b.end_time else '-'}"
    elif batch_map:
        starts = [t for b2 in batch_map.values() if (t := b2.start_time) is not None]
        ends = [t for b2 in batch_map.values() if (t := b2.end_time) is not None]
        s_min = min(starts).strftime("%Y-%m-%d %H:%M") if starts else "-"
        e_max = max(ends).strftime("%Y-%m-%d %H:%M") if ends else "-"
        time_range = f"{s_min} ~ {e_max}"

    # summary stats
    avg_score_val = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else None
    pass_rate_val = round(passed_count / completed_count * 100, 1) if completed_count else None
    summary = f"总人数：{total_arranged}　完成人数：{completed_count}　平均分：{avg_score_val if avg_score_val is not None else '-'}　及格率：{pass_rate_val if pass_rate_val is not None else '-'}%"

    # build HTML report
    import html
    esc = html.escape

    title = f"{esc(exam.name)} 成绩汇总"
    if batch_id and batch_map.get(batch_id):
        title += f" — {esc(batch_map[batch_id].name or f'批次#{batch_id}')}"

    rows_html = ""
    for r in rows:
        score_txt = str(r["score"]) if isinstance(r["score"], str) else f"{r['score']:.1f}"
        correct_txt = f"{r['correct']}/{r['total']}" if isinstance(r["correct"], int) else f"-/{r['total']}"
        cls = ""
        if r["status"] == "通过":
            cls = " pass"
        elif r["status"] == "未通过":
            cls = " fail"
        rows_html += f'<tr><td>{esc(r["name"])}</td><td>{score_txt}</td><td>{correct_txt}</td><td class="st{cls}">{esc(r["status"])}</td></tr>'

    desc = exam.description[:60] if exam.description else "暂无"
    html_report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body{{font-family:"Microsoft YaHei","SimHei",sans-serif;padding:24px 32px;line-height:1.6;color:#222}}
  h1{{border-bottom:2px solid #222;padding-bottom:10px;margin-bottom:16px}}
  table{{border-collapse:collapse;width:100%;margin:12px 0}}
  th,td{{border:1px solid #bbb;padding:6px 10px;text-align:left;vertical-align:top}}
  th{{background:#e8e8e8;font-weight:bold}}
  .lbl{{font-weight:bold;width:100px;white-space:nowrap}}
  .st.pass{{color:#007a00;font-weight:bold}}
  .st.fail{{color:#cc0000;font-weight:bold}}
  .info{{margin:12px 0;font-size:14px}}
</style>
</head>
<body>
<h1>{title}</h1>
<table>
<tr><td class="lbl">描述</td><td>{esc(desc)}</td></tr>
<tr><td class="lbl">考试时长</td><td>{exam.duration_minutes} 分钟</td></tr>
<tr><td class="lbl">考试时间</td><td>{esc(time_range)}</td></tr>
<tr><td class="lbl">及格分数</td><td>{exam.pass_score} 分</td></tr>
<tr><td class="lbl">总题目数</td><td>{total_questions}</td></tr>
<tr><td class="lbl">题型</td><td>{esc(type_str)}</td></tr>
</table>
<p class="info">{summary}</p>
<table>
<thead><tr><th>姓名</th><th>得分</th><th>正确/总数</th><th>状态</th></tr></thead>
<tbody>{rows_html if rows else '<tr><td colspan="4" style="text-align:center;color:#999">暂无数据</td></tr>'}</tbody>
</table>
</body>
</html>"""

    filename = f"成绩汇总-{exam.name}.html"
    return Response(html_report.encode("utf-8"), media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.get("/{exam_id}/take")
async def take_exam(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    assignment = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.exam_id == exam_id,
            ExamAssignment.student_id == current_user.id,
        )
    )).scalars().all()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未安排此考试")

    assign = assignment[-1]
    if assign.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="考试已完成")

    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == assign.batch_id)
    )).scalar_one_or_none()

    now = _dt.now()
    if batch and batch.end_time and batch.end_time < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="考试已过期")
    if batch and batch.start_time and batch.start_time > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="考试尚未开始")

    try:
        paper = json.loads(read_exam_file(exam.id, "exam.json"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷文件不存在")

    questions_no_answers = []
    for q in paper.get("questions", []):
        safe = {"id": q["id"], "type": q["type"], "question": q["question"]}
        if q["type"] in ("single", "multiple"):
            safe["options"] = q.get("options", [])
        if q["type"] == "match":
            safe["left"] = q.get("left", [])
            safe["right"] = q.get("right", [])
        questions_no_answers.append(safe)

    dur = batch.duration_minutes if batch and batch.duration_minutes is not None else exam.duration_minutes
    pscore = batch.pass_score if batch and batch.pass_score is not None else exam.pass_score
    return success_response(ExamTakeResponse(
        id=exam.id, name=exam.name, description=exam.description,
        duration_minutes=dur, pass_score=pscore,
        start_time=batch.start_time if batch else None,
        end_time=batch.end_time if batch else None,
        questions=questions_no_answers,
    ))


@router.post("/{exam_id}/submit")
async def submit_exam(
    exam_id: int,
    request: ExamSubmitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")

    assignment = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.exam_id == exam_id,
            ExamAssignment.student_id == current_user.id,
        )
    )).scalars().all()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未安排此考试")

    assign = assignment[-1]
    if assign.status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="考试已完成")

    try:
        paper = json.loads(read_exam_file(exam.id, "exam.json"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷文件不存在")

    batch = (await session.execute(
        select(ExamBatch).where(ExamBatch.id == assign.batch_id)
    )).scalar_one_or_none()
    pscore = batch.pass_score if batch and batch.pass_score is not None else exam.pass_score

    questions = paper.get("questions", [])
    result = grade_exam(questions, request.answers, pscore)

    correct_answers = {q["id"]: q.get("answer") or q.get("answers") or q.get("matches")
                       for q in questions}
    evaluation = ""
    try:
        evaluation = await evaluate_exam(questions, correct_answers, request.answers)
    except Exception as e:
        logger.warning("AI evaluation failed: %s", e)

    assign.status = "completed"
    assign.score = result["score"]
    assign.passed = result["passed"]
    assign.completed_at = _dt.now()

    student_result = {
        "exam_id": exam.id, "student_id": current_user.id, "batch_id": assign.batch_id,
        "exam_name": exam.name,
        "submitted_at": assign.completed_at.isoformat(),
        "answers": request.answers,
        "score": result["score"], "correct": result["correct"],
        "total": result["total"], "passed": result["passed"],
        "results": result["results"],
        "evaluation": evaluation,
    }
    save_exam_batch_file(exam.id, assign.batch_id, f"{current_user.id}.json",
                          json.dumps(student_result, ensure_ascii=False, indent=2))
    await session.commit()

    return success_response(ExamSubmitResponse(
        completed=result["completed"], correct=result["correct"],
        total=result["total"], score=result["score"],
        passed=result["passed"], evaluation=evaluation,
    ))


@router.get("/{exam_id}/my-result")
async def get_my_result(
    exam_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    exam = (await session.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试卷不存在")
    assignment = (await session.execute(
        select(ExamAssignment).where(
            ExamAssignment.exam_id == exam_id,
            ExamAssignment.student_id == current_user.id,
            ExamAssignment.status == "completed",
        )
    )).scalars().all()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未完成此考试")
    assign = assignment[-1]
    try:
        content = json.loads(read_exam_batch_file(exam.id, assign.batch_id, f"{current_user.id}.json"))
        for r in content.get("results", []):
            r.pop("expected", None)
        try:
            paper = json.loads(read_exam_file(exam.id, "exam.json"))
            sanitized = []
            for q in paper.get("questions", []):
                safe = {"id": q["id"], "type": q["type"], "question": q["question"]}
                if q["type"] in ("single", "multiple"):
                    safe["options"] = q.get("options", [])
                if q["type"] == "match":
                    safe["left"] = q.get("left", [])
                    safe["right"] = q.get("right", [])
                sanitized.append(safe)
            content["questions"] = sanitized
        except (OSError, json.JSONDecodeError):
            content["questions"] = []
        return success_response(content)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试结果不存在")

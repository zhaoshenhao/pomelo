import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_student, require_teacher_or_admin
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.drill import (
    DrillAnswerRequest,
    DrillAnswerResponse,
    DrillBankItem,
    DrillBankSummary,
    DrillQuestionStat,
    DrillSessionStartRequest,
    DrillSessionStartResponse,
)
from app.services.exam_service import grade_answer
from app.services.file_service import (
    list_drill_files,
    read_drill_data,
    read_drill_summary,
    read_qb_file,
    save_drill_data,
    save_drill_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drills", tags=["drills"])

_sessions: dict[str, dict] = {}
_lock = asyncio.Lock()


def _sanitize_question(q: dict) -> dict:
    safe = {"id": q["id"], "type": q["type"], "question": q["question"]}
    if q["type"] in ("single", "multiple"):
        safe["options"] = q.get("options", [])
    if q["type"] == "match":
        safe["left"] = q.get("left", [])
        safe["right"] = q.get("right", [])
    return safe


def _qh_counts(questions: list[dict]) -> tuple[int, dict[str, int]]:
    counts: dict[str, int] = {}
    for q in questions:
        t = q.get("type", "")
        counts[t] = counts.get(t, 0) + 1
    return len(questions), counts


def _select_questions(questions: list[dict], bank_data: dict, count: int) -> list[dict]:
    qid_map = {q["id"]: q for q in questions}
    all_ids = list(qid_map.keys())

    never_tested = [qid for qid in all_ids if qid not in bank_data]
    random.shuffle(never_tested)

    tested_items = [
        (qid, bank_data[qid])
        for qid in all_ids
        if qid in bank_data
    ]
    tested_items.sort(
        key=lambda x: (
            x[1]["correct"] / max(x[1]["tested"], 1),
            x[1].get("last", ""),
        ),
    )

    selected_ids = never_tested[:count]
    remaining = count - len(selected_ids)
    selected_ids += [qid for qid, _ in tested_items[:remaining]]

    return [qid_map[qid] for qid in selected_ids]


def _format_answer_for_display(q: dict) -> object:
    qtype = q.get("type", "")
    if qtype == "multiple":
        return q.get("answers", [])
    if qtype == "match":
        return q.get("matches", {})
    return q.get("answer")


def _qb_counts(qb_id: int) -> tuple[int, dict[str, int]]:
    try:
        content = read_qb_file(qb_id, "qb.json")
        data = json.loads(content)
        stats = data.get("statistics", {})
        return stats.get("total", 0), stats.get("types", {})
    except (OSError, json.JSONDecodeError):
        return 0, {}


@router.get("/banks")
async def list_drill_banks(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    rows = (await session.execute(
        select(QuestionBank).where(QuestionBank.disabled.is_(False)).order_by(QuestionBank.id.desc())
    )).scalars().all()

    drill_data = read_drill_data(current_user.id)
    banks_data = drill_data.get("banks", {})

    items = []
    for qb in rows:
        qb_stats = _qb_counts(qb.id)
        bank_drill = banks_data.get(str(qb.id), {})
        total_ans = sum(e.get("tested", 0) for e in bank_drill.values())
        total_cor = sum(e.get("correct", 0) for e in bank_drill.values())
        ever_corr = sum(1 for e in bank_drill.values() if e.get("correct", 0) > 0)
        acc = round(total_cor / total_ans * 100, 1) if total_ans > 0 else 0.0
        items.append(DrillBankItem(
            id=qb.id,
            name=qb.name,
            description=qb.description,
            question_count=qb_stats[0],
            type_counts=qb_stats[1],
            total_answered=total_ans,
            correct_count=total_cor,
            accuracy=acc,
            ever_correct_questions=ever_corr,
        ))

    return success_response(items)


@router.post("/session/start")
async def start_drill_session(
    request: DrillSessionStartRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    qb = (await session.execute(
        select(QuestionBank).where(QuestionBank.id == request.qb_id)
    )).scalar_one_or_none()

    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")
    if qb.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该题库已被禁止使用")

    try:
        content = read_qb_file(qb.id, "qb.json")
        data = json.loads(content)
        questions = data.get("questions", [])
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库文件不存在")

    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该题库没有题目")

    drill_data = read_drill_data(current_user.id)
    bank_data = drill_data.get("banks", {}).get(str(qb.id), {})

    count = min(10, len(questions))
    selected = _select_questions(questions, bank_data, count)

    session_id = uuid.uuid4().hex
    _sessions[session_id] = {
        "student_id": current_user.id,
        "qb_id": qb.id,
        "question_ids": [q["id"] for q in selected],
        "submitted": set(),
    }

    sanitized = [_sanitize_question(q) for q in selected]

    return success_response(DrillSessionStartResponse(
        session_id=session_id,
        qb_id=qb.id,
        qb_name=qb.name,
        questions=sanitized,
    ))


@router.post("/answer")
async def submit_drill_answer(
    request: DrillAnswerRequest,
    current_user: User = Depends(require_student),
):
    ss = _sessions.get(request.session_id)
    if ss is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="训练会话不存在或已过期")
    if ss["student_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该训练会话")
    if request.question_id not in ss["question_ids"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"题目 {request.question_id} 不在当前训练会话中")

    try:
        content = read_qb_file(ss["qb_id"], "qb.json")
        data = json.loads(content)
        questions = {q["id"]: q for q in data.get("questions", [])}
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库文件不存在")

    question = questions.get(request.question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    correct, info = grade_answer(question, request.answer)

    is_first_submit = request.question_id not in ss["submitted"]
    if is_first_submit:
        ss["submitted"].add(request.question_id)
        tested_count = 0
        correct_count = 0
        async with _lock:
            drill = read_drill_data(current_user.id)
            drill.setdefault("student_id", current_user.id)
            drill.setdefault("banks", {})
            bank = drill["banks"].setdefault(str(ss["qb_id"]), {})
            entry = bank.setdefault(request.question_id, {"tested": 0, "correct": 0, "last": ""})
            entry["tested"] += 1
            if correct:
                entry["correct"] += 1
            entry["last"] = datetime.now(timezone.utc).isoformat()
            tested_count = entry["tested"]
            correct_count = entry["correct"]
            save_drill_data(current_user.id, drill)
    else:
        drill = read_drill_data(current_user.id)
        bank = drill.get("banks", {}).get(str(ss["qb_id"]), {})
        entry = bank.get(request.question_id, {"tested": 0, "correct": 0})
        tested_count = entry.get("tested", 0)
        correct_count = entry.get("correct", 0)

    accuracy = (correct_count / tested_count * 100) if tested_count > 0 else 0.0

    return success_response(DrillAnswerResponse(
        correct=correct,
        correct_answer=_format_answer_for_display(question),
        explanation=question.get("explanation", ""),
        tested=tested_count,
        accuracy=round(accuracy, 1),
    ))


def _compute_summary(qb_id: int, qb_name: str) -> DrillBankSummary:
    try:
        content = read_qb_file(qb_id, "qb.json")
        data = json.loads(content)
        qb_questions = {q["id"]: q for q in data.get("questions", [])}
    except (OSError, json.JSONDecodeError):
        qb_questions = {}

    per_q: dict[str, dict] = {}
    for qid, q in qb_questions.items():
        per_q[qid] = {
            "question_id": qid,
            "type": q.get("type", ""),
            "question": q.get("question", ""),
            "total_attempts": 0,
            "correct": 0,
            "accuracy": 0.0,
        }

    student_ids: set[int] = set()
    total_attempts = 0
    total_correct = 0

    for filepath in list_drill_files():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                student_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        sid = student_data.get("student_id")
        bank_data = student_data.get("banks", {}).get(str(qb_id), {})
        has_attempt = False
        for qid, entry in bank_data.items():
            t = entry.get("tested", 0)
            c = entry.get("correct", 0)
            if t > 0 and qid in per_q:
                per_q[qid]["total_attempts"] += t
                per_q[qid]["correct"] += c
                total_attempts += t
                total_correct += c
                has_attempt = True
        if has_attempt and sid is not None:
            student_ids.add(sid)

    for qid in per_q:
        pa = per_q[qid]["total_attempts"]
        pc = per_q[qid]["correct"]
        per_q[qid]["accuracy"] = round(pc / pa * 100, 1) if pa > 0 else 0.0

    def _num_id(qid: str) -> int:
        digits = "".join(c for c in qid if c.isdigit())
        return int(digits) if digits else 0

    questions_list = sorted(
        per_q.values(),
        key=lambda x: (0 if x["total_attempts"] > 0 else 1, _num_id(x["question_id"])),
    )

    used_qs = sum(1 for q in per_q.values() if q["total_attempts"] > 0)
    ever_corr = sum(1 for q in per_q.values() if q["correct"] > 0)

    accuracy = round(total_correct / total_attempts * 100, 1) if total_attempts > 0 else 0.0

    return DrillBankSummary(
        qb_id=qb_id,
        qb_name=qb_name,
        total_students=len(student_ids),
        used_questions=used_qs,
        total_attempts=total_attempts,
        ever_correct_questions=ever_corr,
        total_correct=total_correct,
        accuracy=accuracy,
        updated_at=datetime.now(timezone.utc).isoformat(),
        questions=[DrillQuestionStat(**q) for q in questions_list],
    )


@router.get("/banks/{qb_id}/summary")
async def get_bank_summary(
    qb_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    qb = (await session.execute(
        select(QuestionBank).where(QuestionBank.id == qb_id)
    )).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")

    cached = read_drill_summary(qb_id)
    if cached is not None:
        return success_response(cached)

    summary = _compute_summary(qb_id, qb.name)
    save_drill_summary(qb_id, summary.model_dump())
    return success_response(summary.model_dump())


@router.post("/banks/{qb_id}/summary/regenerate")
async def regenerate_bank_summary(
    qb_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    qb = (await session.execute(
        select(QuestionBank).where(QuestionBank.id == qb_id)
    )).scalar_one_or_none()
    if qb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库不存在")

    summary = _compute_summary(qb_id, qb.name)
    save_drill_summary(qb_id, summary.model_dump())
    return success_response(summary.model_dump())

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_student, require_teacher_or_admin
from app.models.department import Department
from app.models.document import Document
from app.models.exam import Exam, ExamAssignment, ExamBatch
from app.models.question_bank import QuestionBank
from app.models.study_assignment import StudyAssignment
from app.models.study_material import StudyMaterial
from app.models.user import User, UserRole
from app.schemas.common import success_response
from app.schemas.dashboard import (
    DashboardCounts,
    RecentExamInfo,
    StudentCourseInfo,
    StudentDashboardResponse,
    StudentDrillInfo,
    StudentExamInfo,
    StudyProgressInfo,
    TeacherDashboardResponse,
)
from app.services.file_service import read_drill_data, read_exam_file, read_qb_file


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _paper_counts(exam_id: int) -> tuple[int, dict[str, int]]:
    try:
        content = read_exam_file(exam_id, "exam.json")
        data = json.loads(content)
        questions = data.get("questions", [])
        counts: dict[str, int] = {}
        for q in questions:
            t = q.get("type", "")
            counts[t] = counts.get(t, 0) + 1
        return len(questions), counts
    except (OSError, json.JSONDecodeError):
        return 0, {}


@router.get("/teacher")
async def teacher_dashboard(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    doc_total = (await session.execute(select(func.count(Document.id)))).scalar() or 0
    stu_count = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.STUDENT))).scalar() or 0
    tea_count = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.TEACHER))).scalar() or 0
    adm_count = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.ADMIN))).scalar() or 0
    dept_count = (await session.execute(select(func.count(Department.id)))).scalar() or 0
    qb_count = (await session.execute(select(func.count(QuestionBank.id)))).scalar() or 0
    sm_count = (await session.execute(select(func.count(StudyMaterial.id)))).scalar() or 0
    exam_count = (await session.execute(select(func.count(Exam.id)))).scalar() or 0

    counts = DashboardCounts(
        documents=doc_total,
        students=stu_count,
        teachers=tea_count,
        admins=adm_count,
        departments=dept_count,
        question_banks=qb_count,
        study_materials=sm_count,
        exams=exam_count,
    )

    all_batches = (await session.execute(
        select(ExamBatch, Exam)
        .join(Exam, ExamBatch.exam_id == Exam.id)
        .where(ExamBatch.disabled.is_(False))
    )).all()

    def _sort_key(batch: ExamBatch) -> tuple:
        t = batch.start_time or batch.end_time or batch.created_at
        return t if t else datetime(2000, 1, 1, tzinfo=timezone.utc)

    sorted_batches = sorted(all_batches, key=lambda x: _sort_key(x[0]), reverse=True)[:3]

    all_batch_ids = [b.id for b, _ in sorted_batches]
    assign_map: dict[int, list[ExamAssignment]] = {}
    if all_batch_ids:
        all_assigns = (await session.execute(
            select(ExamAssignment).where(ExamAssignment.batch_id.in_(all_batch_ids))
        )).scalars().all()
        for a in all_assigns:
            assign_map.setdefault(a.batch_id, []).append(a)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    recent_exams = []
    for batch, exam in sorted_batches:
        qc, tc = _paper_counts(exam.id)
        assigns = assign_map.get(batch.id, [])
        arranged = len(assigns)
        completed = [a for a in assigns if a.status == "completed"]
        c_count = len(completed)
        p_count = sum(1 for a in completed if a.passed)
        pass_rate = round(p_count / c_count * 100, 1) if c_count else None
        scores = [a.score for a in completed if a.score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        batch_start = batch.start_time
        batch_end = batch.end_time

        started = batch_start is None or batch_start <= now
        ended = batch_end is not None and batch_end < now

        recent_exams.append(RecentExamInfo(
            exam_id=exam.id,
            batch_id=batch.id,
            name=batch.name or exam.name,
            start_time=batch_start.isoformat() if batch_start else None,
            end_time=batch_end.isoformat() if batch_end else None,
            duration_minutes=batch.duration_minutes if batch.duration_minutes is not None else exam.duration_minutes,
            pass_score=batch.pass_score if batch.pass_score is not None else exam.pass_score,
            question_count=qc,
            type_counts=tc,
            arranged_count=arranged,
            completed_count=c_count if started or ended else None,
            pass_rate=pass_rate if started or ended else None,
            average_score=avg_score if started or ended else None,
            started=started,
            ended=ended,
        ))

    materials = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.active).order_by(StudyMaterial.id.desc()).limit(3)
    )).scalars().all()
    mat_ids = [m.id for m in materials]
    mat_assignment_map: dict[int, list[StudyAssignment]] = {}
    if mat_ids:
        sa_rows = (await session.execute(
            select(StudyAssignment).where(StudyAssignment.material_id.in_(mat_ids))
        )).scalars().all()
        for sa in sa_rows:
            mat_assignment_map.setdefault(sa.material_id, []).append(sa)

    progress = []
    for m in materials:
        assignments = mat_assignment_map.get(m.id, [])
        started_count = len(assignments)
        completed_count = sum(1 for a in assignments if a.status == "completed")
        total_seconds = sum(a.total_study_seconds for a in assignments)
        avg_seconds = round(total_seconds / started_count, 1) if started_count else 0.0
        avg_reads = round(m.read_count / started_count, 1) if started_count else 0.0
        progress.append(StudyProgressInfo(
            material_id=m.id,
            name=m.name,
            min_minutes=m.min_minutes,
            started_count=started_count,
            completed_count=completed_count,
            total_study_seconds=total_seconds,
            avg_study_seconds=avg_seconds,
            avg_read_count=avg_reads,
        ))

    return success_response(TeacherDashboardResponse(
        counts=counts,
        recent_exams=recent_exams,
        study_progress=progress,
    ))


@router.get("/student")
async def student_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    assignments = (await session.execute(
        select(ExamAssignment).where(ExamAssignment.student_id == current_user.id)
    )).scalars().all()

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

    in_progress_items: list[dict] = []
    upcoming_items: list[dict] = []
    completed_items: list[dict] = []

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
        qc, tc = _paper_counts(e.id)

        item = {
            "assignment_id": a.id, "exam_id": a.exam_id, "batch_id": a.batch_id,
            "name": batch.name or e.name if batch else e.name,
            "start_time": start.isoformat() if start else None,
            "end_time": end.isoformat() if end else None,
            "duration_minutes": dur, "pass_score": pscore,
            "question_count": qc, "type_counts": tc,
            "status": a.status,
            "score": a.score, "passed": a.passed,
        }

        if a.status == "completed":
            completed_items.append(item)
        elif end and end < now:
            continue
        elif start and start > now:
            upcoming_items.append(item)
        else:
            in_progress_items.append(item)

    exam_cards = in_progress_items[:3]
    remaining = 3 - len(exam_cards)
    exam_cards += upcoming_items[:remaining]
    remaining = 3 - len(exam_cards)
    exam_cards += completed_items[:remaining]

    student_exams = [StudentExamInfo(**item) for item in exam_cards]

    materials = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.active).order_by(StudyMaterial.id)
    )).scalars().all()
    mat_ids = [m.id for m in materials]
    sa_map: dict[int, StudyAssignment] = {}
    if mat_ids:
        sa_rows = (await session.execute(
            select(StudyAssignment).where(
                StudyAssignment.material_id.in_(mat_ids),
                StudyAssignment.student_id == current_user.id,
            )
        )).scalars().all()
        sa_map = {a.material_id: a for a in sa_rows}

    courses = []
    for m in materials:
        a = sa_map.get(m.id)
        courses.append(StudentCourseInfo(
            material_id=m.id,
            material_name=m.name,
            material_description=m.description,
            document_names=m.document_names,
            min_minutes=m.min_minutes,
            has_started=bool(a) if a else False,
            completed=a.status == "completed" if a else False,
            total_study_seconds=a.total_study_seconds if a else 0,
            last_study_at=a.last_study_at.isoformat() if a and a.last_study_at else None,
            assignment_id=a.id if a else None,
        ))
    courses = courses[:3]

    qb_rows = (await session.execute(
        select(QuestionBank).where(QuestionBank.disabled.is_(False)).order_by(QuestionBank.id.desc())
    )).scalars().all()
    drill_data = read_drill_data(current_user.id)
    banks_data = drill_data.get("banks", {})
    drills = []
    for qb in qb_rows[:3]:
        try:
            content = read_qb_file(qb.id, "qb.json")
            qb_data = json.loads(content)
            stats = qb_data.get("statistics", {})
        except (OSError, json.JSONDecodeError):
            stats = {}
        bank_drill = banks_data.get(str(qb.id), {})
        total_ans = sum(e.get("tested", 0) for e in bank_drill.values())
        total_cor = sum(e.get("correct", 0) for e in bank_drill.values())
        ever_corr = sum(1 for e in bank_drill.values() if e.get("correct", 0) > 0)
        acc = round(total_cor / total_ans * 100, 1) if total_ans > 0 else 0.0
        drills.append(StudentDrillInfo(
            id=qb.id, name=qb.name, description=qb.description,
            question_count=stats.get("total", 0),
            type_counts=stats.get("types", {}),
            total_answered=total_ans, correct_count=total_cor,
            accuracy=acc, ever_correct_questions=ever_corr,
        ))

    return success_response(StudentDashboardResponse(
        exams=student_exams, courses=courses, drills=drills,
    ))

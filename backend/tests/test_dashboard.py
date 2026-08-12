import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.document import Document, DocumentLibrary
from app.models.exam import Exam, ExamAssignment, ExamBatch
from app.models.question_bank import QuestionBank
from app.models.study_assignment import StudyAssignment
from app.models.study_material import StudyMaterial
from app.services.file_service import save_exam_file, save_qb_file

MOCK_EXAM_QUESTIONS = [
    {"id": "q1", "type": "single", "question": "singles", "options": ["A", "B", "C", "D"], "answer": "A"},
    {"id": "q2", "type": "multiple", "question": "multis", "options": ["A", "B", "C"], "answers": ["A", "C"]},
    {"id": "q3", "type": "true_false", "question": "tf", "answer": True},
]

MOCK_QB_DATA = {
    "questions": MOCK_EXAM_QUESTIONS,
    "statistics": {"total": 3, "types": {"single": 1, "multiple": 1, "true_false": 1}},
}


async def _reg_admin(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "dash_admin", "email": "dash_admin@test.com",
        "phone": "13900000001", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": "dash_admin", "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _reg_student(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "dash_stu", "email": "dash_stu@test.com",
        "phone": "13900000002", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": "dash_stu", "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _ensure_student(client: AsyncClient) -> str:
    await _reg_admin(client)
    return await _reg_student(client)


class TestTeacherDashboard:
    @pytest.mark.asyncio
    async def test_counts(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)

        dept = Department(name="d1")
        db_session.add(dept)
        await db_session.flush()

        lib = DocumentLibrary(name="dlib", local_path="/s/")
        db_session.add(lib)
        await db_session.flush()
        doc = Document(library_id=lib.id, filename="f.md", path="/s/f.md", uploaded_by=1)
        db_session.add(doc)
        await db_session.commit()

        await client.post("/api/users", json={
            "username": "dash_teacher", "email": "dash_teacher@test.com",
            "phone": "13900000003", "department_id": dept.id, "role": "teacher", "password": "pwd123",
        }, headers={"Authorization": f"Bearer {admin}"})

        _ = await _reg_student(client)

        prom_r = await client.post("/api/ai-prompts", json={
            "name": "dp", "prompt": "p", "prompt_type": "exam",
        }, headers={"Authorization": f"Bearer {admin}"})
        pid = prom_r.json()["data"]["id"]

        qb = QuestionBank(name="dqb", library_id=lib.id, document_names="", prompt_id=pid, prompt_text="", created_by=1)
        db_session.add(qb)
        sm = StudyMaterial(name="dsm", library_id=lib.id, document_names="", prompt_id=pid, min_minutes=10, created_by=1, active=True)
        db_session.add(sm)
        exam = Exam(name="dex", duration_minutes=30, pass_score=60, created_by=1)
        db_session.add(exam)
        await db_session.commit()

        r = await client.get("/api/dashboard/teacher", headers={"Authorization": f"Bearer {admin}"})
        assert r.status_code == 200
        c = r.json()["data"]["counts"]
        assert c["documents"] == 1
        assert c["students"] == 1
        assert c["teachers"] == 1
        assert c["admins"] == 1
        assert c["departments"] == 1
        assert c["question_banks"] == 1
        assert c["study_materials"] == 1
        assert c["exams"] == 1

    @pytest.mark.asyncio
    async def test_recent_exams_filters_disabled(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        exam = Exam(name="recent_ex", duration_minutes=30, pass_score=60, created_by=1)
        db_session.add(exam)
        await db_session.flush()
        batch1 = ExamBatch(exam_id=exam.id, name="b1", disabled=False, arranged_by=1)
        batch2 = ExamBatch(exam_id=exam.id, name="b2", disabled=True, arranged_by=1)
        db_session.add_all([batch1, batch2])
        await db_session.commit()
        save_exam_file(exam.id, "exam.json", json.dumps({"questions": MOCK_EXAM_QUESTIONS}))

        r = await client.get("/api/dashboard/teacher", headers={"Authorization": f"Bearer {admin}"})
        data = r.json()["data"]
        assert len(data["recent_exams"]) == 1
        assert data["recent_exams"][0]["batch_id"] == batch1.id
        assert data["recent_exams"][0]["question_count"] == 3
        assert data["recent_exams"][0]["type_counts"]["single"] == 1

    @pytest.mark.asyncio
    async def test_recent_exams_max3(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        exam = Exam(name="max3_ex", duration_minutes=30, pass_score=60, created_by=1)
        db_session.add(exam)
        await db_session.flush()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for i in range(5):
            batch = ExamBatch(exam_id=exam.id, name=f"b{i}", disabled=False, arranged_by=1, start_time=now.replace(second=i))
            db_session.add(batch)
        await db_session.commit()
        save_exam_file(exam.id, "exam.json", json.dumps({"questions": []}))

        r = await client.get("/api/dashboard/teacher", headers={"Authorization": f"Bearer {admin}"})
        assert len(r.json()["data"]["recent_exams"]) == 3

    @pytest.mark.asyncio
    async def test_study_progress_active_only(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        await _reg_student(client)

        prom_r = await client.post("/api/ai-prompts", json={
            "name": "dsp", "prompt": "p", "prompt_type": "exam",
        }, headers={"Authorization": f"Bearer {admin}"})
        pid = prom_r.json()["data"]["id"]

        lib = DocumentLibrary(name="dslib", local_path="/ds/")
        db_session.add(lib)
        await db_session.flush()

        sm_active = StudyMaterial(name="active_m", library_id=lib.id, document_names="", prompt_id=pid, min_minutes=15, created_by=1, active=True)
        sm_inactive = StudyMaterial(name="inactive_m", library_id=lib.id, document_names="", prompt_id=pid, min_minutes=10, created_by=1, active=False)
        db_session.add_all([sm_active, sm_inactive])
        await db_session.flush()

        sa = StudyAssignment(material_id=sm_active.id, student_id=2, status="completed", total_study_seconds=900)
        db_session.add(sa)
        await db_session.commit()

        r = await client.get("/api/dashboard/teacher", headers={"Authorization": f"Bearer {admin}"})
        data = r.json()["data"]
        assert len(data["study_progress"]) == 1
        sp = data["study_progress"][0]
        assert sp["name"] == "active_m"
        assert sp["started_count"] == 1
        assert sp["completed_count"] == 1
        assert sp["total_study_seconds"] == 900

    @pytest.mark.asyncio
    async def test_student_forbidden(self, client: AsyncClient):
        token = await _ensure_student(client)
        r = await client.get("/api/dashboard/teacher", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


class TestStudentDashboard:
    @pytest.mark.asyncio
    async def test_exam_priority_order(self, client: AsyncClient, db_session: AsyncSession):
        await _reg_admin(client)
        student = await _reg_student(client)

        exam = Exam(name="prio_ex", duration_minutes=30, pass_score=60, created_by=1)
        db_session.add(exam)
        await db_session.flush()
        save_exam_file(exam.id, "exam.json", json.dumps({"questions": MOCK_EXAM_QUESTIONS}))

        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        b_upcoming = ExamBatch(exam_id=exam.id, name="b_up", disabled=False, arranged_by=1, start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=4))
        b_inprog = ExamBatch(exam_id=exam.id, name="b_ip", disabled=False, arranged_by=1, start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1))
        b_completed = ExamBatch(exam_id=exam.id, name="b_cp", disabled=False, arranged_by=1, start_time=now - timedelta(hours=4), end_time=now - timedelta(hours=2))
        db_session.add_all([b_upcoming, b_inprog, b_completed])
        await db_session.flush()

        a_up = ExamAssignment(exam_id=exam.id, batch_id=b_upcoming.id, student_id=2, status="assigned")
        a_ip = ExamAssignment(exam_id=exam.id, batch_id=b_inprog.id, student_id=2, status="assigned")
        a_cp = ExamAssignment(exam_id=exam.id, batch_id=b_completed.id, student_id=2, status="completed", score=80, passed=True)
        db_session.add_all([a_up, a_ip, a_cp])
        await db_session.commit()

        r = await client.get("/api/dashboard/student", headers={"Authorization": f"Bearer {student}"})
        exams = r.json()["data"]["exams"]
        assert len(exams) == 3
        assert exams[0]["batch_id"] == b_inprog.id
        assert exams[1]["batch_id"] == b_upcoming.id
        assert exams[2]["batch_id"] == b_completed.id
        assert exams[2]["score"] == 80
        assert exams[2]["passed"] is True

    @pytest.mark.asyncio
    async def test_courses(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        student = await _reg_student(client)

        prom_r = await client.post("/api/ai-prompts", json={
            "name": "dcp", "prompt": "p", "prompt_type": "exam",
        }, headers={"Authorization": f"Bearer {admin}"})
        pid = prom_r.json()["data"]["id"]

        lib = DocumentLibrary(name="dclib", local_path="/dc/")
        db_session.add(lib)
        await db_session.flush()

        sm = StudyMaterial(name="course_m", document_names="a.md", prompt_id=pid, library_id=lib.id, min_minutes=20, created_by=1, active=True)
        db_session.add(sm)
        await db_session.flush()
        sa = StudyAssignment(material_id=sm.id, student_id=2, status="assigned", total_study_seconds=300)
        db_session.add(sa)
        await db_session.commit()

        r = await client.get("/api/dashboard/student", headers={"Authorization": f"Bearer {student}"})
        courses = r.json()["data"]["courses"]
        assert len(courses) == 1
        assert courses[0]["material_name"] == "course_m"
        assert courses[0]["min_minutes"] == 20
        assert courses[0]["has_started"] is True
        assert courses[0]["completed"] is False

    @pytest.mark.asyncio
    async def test_drills(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        student = await _reg_student(client)

        prom_r = await client.post("/api/ai-prompts", json={
            "name": "ddp", "prompt": "p", "prompt_type": "exam",
        }, headers={"Authorization": f"Bearer {admin}"})
        pid = prom_r.json()["data"]["id"]

        lib = DocumentLibrary(name="ddlib", local_path="/dd/")
        db_session.add(lib)
        await db_session.flush()

        qb = QuestionBank(name="ddrill", library_id=lib.id, document_names="", prompt_id=pid, prompt_text="", created_by=1, disabled=False)
        db_session.add(qb)
        await db_session.commit()
        await db_session.refresh(qb)
        qb_data = dict(MOCK_QB_DATA)
        qb_data["id"] = qb.id
        save_qb_file(qb.id, "qb.json", json.dumps(qb_data))

        r = await client.get("/api/dashboard/student", headers={"Authorization": f"Bearer {student}"})
        drills = r.json()["data"]["drills"]
        assert len(drills) == 1
        assert drills[0]["name"] == "ddrill"
        assert drills[0]["question_count"] == 3
        assert drills[0]["total_answered"] == 0

    @pytest.mark.asyncio
    async def test_exam_question_counts_present(self, client: AsyncClient, db_session: AsyncSession):
        await _reg_admin(client)
        student = await _reg_student(client)

        exam = Exam(name="qcount_ex", duration_minutes=30, pass_score=60, created_by=1)
        db_session.add(exam)
        await db_session.flush()
        batch = ExamBatch(exam_id=exam.id, name="b1", disabled=False, arranged_by=1, start_time=None, end_time=None)
        db_session.add(batch)
        await db_session.flush()
        a = ExamAssignment(exam_id=exam.id, batch_id=batch.id, student_id=2, status="assigned")
        db_session.add(a)
        await db_session.commit()
        save_exam_file(exam.id, "exam.json", json.dumps({"questions": MOCK_EXAM_QUESTIONS}))

        r = await client.get("/api/dashboard/student", headers={"Authorization": f"Bearer {student}"})
        exam_data = r.json()["data"]["exams"][0]
        assert exam_data["question_count"] == 3
        assert exam_data["type_counts"]["single"] == 1
        assert exam_data["type_counts"]["multiple"] == 1
        assert exam_data["type_counts"]["true_false"] == 1

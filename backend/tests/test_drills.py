import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question_bank import QuestionBank
from app.services.file_service import save_qb_file

MOCK_DRILL_QUESTIONS = [
    {"id": "q1", "type": "single", "question": "\u5355\u9009\u9898", "options": ["A.a", "B.b", "C.c", "D.d"], "answer": "A", "explanation": "\u9009A"},
    {"id": "q2", "type": "multiple", "question": "\u591a\u9009\u9898", "options": ["A.x", "B.y", "C.z"], "answers": ["A", "C"], "explanation": "\u591a\u9009"},
    {"id": "q3", "type": "true_false", "question": "\u5bf9\u9519\u9898", "answer": True, "explanation": "\u5bf9\u7684"},
    {"id": "q4", "type": "fill", "question": "\u586b\u7a7a", "answer": "hello", "explanation": "\u586bhello"},
    {"id": "q5", "type": "match", "question": "\u5339\u914d", "left": ["A", "B"], "right": ["1", "2"], "matches": {"A": "1", "B": "2"}, "explanation": "\u5339\u914d\u9898"},
]

MOCK_QB_DATA = {
    "questions": MOCK_DRILL_QUESTIONS,
    "statistics": {"total": 5, "types": {"single": 1, "multiple": 1, "true_false": 1, "fill": 1, "match": 1}},
}


async def _reg_admin(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "drill_admin", "email": "drill_admin@test.com",
        "phone": "13900000001", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": "drill_admin", "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _reg_student(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "drill_stu", "email": "drill_stu@test.com",
        "phone": "13900000002", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": "drill_stu", "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _ensure_student(client: AsyncClient) -> str:
    await _reg_admin(client)
    return await _reg_student(client)


async def _make_qb(client: AsyncClient, admin_token: str, db_session: AsyncSession, disabled: bool = False, label: str | None = None) -> int:
    if label is None:
        label = "disabled" if disabled else "active"
    lib_r = await client.post("/api/libraries", json={"name": f"drill_lib_{label}", "description": "test"}, headers={"Authorization": f"Bearer {admin_token}"})
    lib_id = lib_r.json()["data"]["id"]

    prompt_r = await client.post("/api/ai-prompts", json={"name": f"drill_prompt_{label}", "prompt": "test", "prompt_type": "exam"}, headers={"Authorization": f"Bearer {admin_token}"})
    prompt_id = prompt_r.json()["data"]["id"]

    qb = QuestionBank(
        name=f"drill_qb_{label}",
        library_id=lib_id,
        document_names="",
        prompt_id=prompt_id,
        prompt_text="",
        created_by=1,
        disabled=disabled,
    )
    db_session.add(qb)
    await db_session.commit()
    await db_session.refresh(qb)

    qb_data = dict(MOCK_QB_DATA)
    qb_data["id"] = qb.id
    save_qb_file(qb.id, "qb.json", json.dumps(qb_data, ensure_ascii=False))
    return qb.id


class TestDrillBanks:
    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient):
        token = await _ensure_student(client)
        r = await client.get("/api/drills/banks", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["data"] == []

    @pytest.mark.asyncio
    async def test_list_with_banks(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        await _make_qb(client, admin, db_session, disabled=False)

        student = await _reg_student(client)
        r = await client.get("/api/drills/banks", headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        items = r.json()["data"]
        assert len(items) == 1
        assert items[0]["question_count"] == 5
        assert items[0]["type_counts"]["single"] == 1
        assert items[0]["type_counts"]["multiple"] == 1

    @pytest.mark.asyncio
    async def test_excludes_disabled(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        await _make_qb(client, admin, db_session, disabled=False)
        await _make_qb(client, admin, db_session, disabled=True)

        student = await _reg_student(client)
        r = await client.get("/api/drills/banks", headers={"Authorization": f"Bearer {student}"})
        items = r.json()["data"]
        assert len(items) == 1
        assert "disabled" not in items[0]["name"]


class TestDrillSession:
    @pytest.mark.asyncio
    async def test_start_happy(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        r = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "session_id" in data
        assert data["qb_id"] == qb_id
        assert len(data["questions"]) == 5
        for q in data["questions"]:
            assert "answer" not in q
            assert "answers" not in q
            assert "matches" not in q
            assert "explanation" not in q

    @pytest.mark.asyncio
    async def test_start_disabled_bank(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=True)
        student = await _reg_student(client)

        r = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 400
        assert "禁止" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_not_found(self, client: AsyncClient):
        student = await _ensure_student(client)
        r = await client.post("/api/drills/session/start", json={"qb_id": 9999}, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 404


class TestDrillAnswer:
    @pytest.mark.asyncio
    async def test_answer_correct(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        q = next(qq for qq in qs if qq["type"] == "single")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": q["id"], "answer": "A",
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["correct"] is True
        assert data["tested"] == 1
        assert data["accuracy"] == 100.0

    @pytest.mark.asyncio
    async def test_answer_wrong(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        q = next(qq for qq in qs if qq["type"] == "single")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": q["id"], "answer": "B",
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["correct"] is False
        assert data["correct_answer"] == "A"
        assert data["tested"] == 1
        assert data["accuracy"] == 0.0

    @pytest.mark.asyncio
    async def test_answer_idempotent(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        q = next(qq for qq in qs if qq["type"] == "single")

        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": q["id"], "answer": "A"}, headers={"Authorization": f"Bearer {student}"})
        r2 = await client.post("/api/drills/answer", json={"session_id": sid, "question_id": q["id"], "answer": "B"}, headers={"Authorization": f"Bearer {student}"})
        data = r2.json()["data"]
        assert data["tested"] == 1

    @pytest.mark.asyncio
    async def test_answer_invalid_session(self, client: AsyncClient):
        student = await _ensure_student(client)
        r = await client.post("/api/drills/answer", json={
            "session_id": "nonexistent", "question_id": "q1", "answer": "A",
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_fill_answer(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        fill_q = next(q for q in qs if q["type"] == "fill")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": fill_q["id"], "answer": "hello",
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        assert r.json()["data"]["correct"] is True

    @pytest.mark.asyncio
    async def test_true_false_answer(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        tf_q = next(q for q in qs if q["type"] == "true_false")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": tf_q["id"], "answer": True,
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        assert r.json()["data"]["correct"] is True

    @pytest.mark.asyncio
    async def test_multiple_answer(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        q = next(qq for qq in qs if qq["type"] == "multiple")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": q["id"], "answer": ["A", "C"],
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        assert r.json()["data"]["correct"] is True

    @pytest.mark.asyncio
    async def test_match_answer(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        q = next(qq for qq in qs if qq["type"] == "match")

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": q["id"], "answer": {"A": "1", "B": "2"},
        }, headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 200
        assert r.json()["data"]["correct"] is True

    @pytest.mark.asyncio
    async def test_wrong_user_session(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student1 = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student1}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        first_qid = qs[0]["id"]

        await client.post("/api/auth/register", json={
            "username": "drill_stu2", "email": "drill_stu2@test.com",
            "phone": "13900000003", "department": "Dept", "password": "pwd123",
        })
        resp = await client.post("/api/auth/login", json={"username": "drill_stu2", "password": "pwd123"})
        student2 = resp.json()["data"]["access_token"]

        r = await client.post("/api/drills/answer", json={
            "session_id": sid, "question_id": first_qid, "answer": "A",
        }, headers={"Authorization": f"Bearer {student2}"})
        assert r.status_code == 403


class TestDrillListStats:
    @pytest.mark.asyncio
    async def test_stats_after_answers(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        sq = next(q for q in qs if q["type"] == "single")
        mq = next(q for q in qs if q["type"] == "multiple")

        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": sq["id"], "answer": "A"}, headers={"Authorization": f"Bearer {student}"})
        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": mq["id"], "answer": ["A", "C"]}, headers={"Authorization": f"Bearer {student}"})

        r = await client.get("/api/drills/banks", headers={"Authorization": f"Bearer {student}"})
        items = r.json()["data"]
        b = next(b for b in items if b["id"] == qb_id)
        assert b["total_answered"] == 2
        assert b["correct_count"] == 2
        assert b["accuracy"] == 100.0
        assert b["ever_correct_questions"] == 2

    @pytest.mark.asyncio
    async def test_stats_none(self, client: AsyncClient):
        token = await _ensure_student(client)
        r = await client.get("/api/drills/banks", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        for b in r.json()["data"]:
            assert b["total_answered"] == 0
            assert b["accuracy"] == 0.0
            assert b["ever_correct_questions"] == 0


class TestDrillSummary:
    @pytest.mark.asyncio
    async def test_summary_empty(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)

        r = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {admin}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_students"] == 0
        assert data["used_questions"] == 0
        assert data["total_attempts"] == 0
        assert data["ever_correct_questions"] == 0
        assert data["total_correct"] == 0
        assert data["accuracy"] == 0.0
        for q in data["questions"]:
            assert q["total_attempts"] == 0

    @pytest.mark.asyncio
    async def test_summary_with_data(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        sq = next(q for q in qs if q["type"] == "single")

        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": sq["id"], "answer": "A"}, headers={"Authorization": f"Bearer {student}"})

        r = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {admin}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_students"] == 1
        assert data["used_questions"] == 1
        assert data["total_attempts"] == 1
        assert data["ever_correct_questions"] == 1
        assert data["total_correct"] == 1
        assert data["accuracy"] == 100.0

    @pytest.mark.asyncio
    async def test_summary_cache_and_regenerate(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student1 = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student1}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        sq = next(q for q in qs if q["type"] == "single")

        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": sq["id"], "answer": "A"}, headers={"Authorization": f"Bearer {student1}"})

        r1 = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {admin}"})
        assert r1.json()["data"]["total_attempts"] == 1

        await client.post("/api/auth/register", json={
            "username": "drill_stu2", "email": "drill_stu2@test.com",
            "phone": "13900000003", "department": "Dept", "password": "pwd123",
        })
        resp = await client.post("/api/auth/login", json={"username": "drill_stu2", "password": "pwd123"})
        student2 = resp.json()["data"]["access_token"]

        start2 = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student2}"})
        sid2 = start2.json()["data"]["session_id"]
        qs2 = start2.json()["data"]["questions"]
        sq2 = next(q for q in qs2 if q["type"] == "single")

        await client.post("/api/drills/answer", json={"session_id": sid2, "question_id": sq2["id"], "answer": "A"}, headers={"Authorization": f"Bearer {student2}"})

        r2 = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {admin}"})
        assert r2.json()["data"]["total_attempts"] == 1

        r3 = await client.post(f"/api/drills/banks/{qb_id}/summary/regenerate", headers={"Authorization": f"Bearer {admin}"})
        assert r3.json()["data"]["total_attempts"] == 2
        assert r3.json()["data"]["total_students"] == 2

    @pytest.mark.asyncio
    async def test_regenerate(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)

        r = await client.post(f"/api/drills/banks/{qb_id}/summary/regenerate", headers={"Authorization": f"Bearer {admin}"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["qb_id"] == qb_id
        assert "questions" in data

    @pytest.mark.asyncio
    async def test_summary_student_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        r = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {student}"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_summary_all_questions_present(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)

        r = await client.get(f"/api/drills/banks/{qb_id}/summary", headers={"Authorization": f"Bearer {admin}"})
        assert r.status_code == 200
        questions = r.json()["data"]["questions"]
        assert len(questions) == 5

    @pytest.mark.asyncio
    async def test_summary_sort_order(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_id = await _make_qb(client, admin, db_session, disabled=False)
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_id}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        qs = start.json()["data"]["questions"]
        tf_q = next(q for q in qs if q["type"] == "true_false")

        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": tf_q["id"], "answer": True}, headers={"Authorization": f"Bearer {student}"})

        r = await client.post(f"/api/drills/banks/{qb_id}/summary/regenerate", headers={"Authorization": f"Bearer {admin}"})
        qids = [q["question_id"] for q in r.json()["data"]["questions"]]
        tf_qid = tf_q["id"]
        expected_first = tf_qid
        assert qids[0] == expected_first

    @pytest.mark.asyncio
    async def test_summary_total_students_excludes_other_banks(self, client: AsyncClient, db_session: AsyncSession):
        admin = await _reg_admin(client)
        qb_a = await _make_qb(client, admin, db_session, disabled=False, label="A")
        qb_b = await _make_qb(client, admin, db_session, disabled=False, label="B")
        student = await _reg_student(client)

        start = await client.post("/api/drills/session/start", json={"qb_id": qb_a}, headers={"Authorization": f"Bearer {student}"})
        sid = start.json()["data"]["session_id"]
        first_qid = start.json()["data"]["questions"][0]["id"]
        await client.post("/api/drills/answer", json={"session_id": sid, "question_id": first_qid, "answer": "B"}, headers={"Authorization": f"Bearer {student}"})

        r = await client.post(f"/api/drills/banks/{qb_b}/summary/regenerate", headers={"Authorization": f"Bearer {admin}"})
        assert r.json()["data"]["total_students"] == 0

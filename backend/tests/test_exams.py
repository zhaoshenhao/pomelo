import asyncio

import pytest
from httpx import AsyncClient
from unittest.mock import patch

from tests.utils import unique_library_name

MOCK_QB_DATA = {
    "questions": [
        {"id": "q1", "type": "single", "question": "Q1", "options": ["A.a","B.b","C.c","D.d"], "answer": "A"},
        {"id": "q2", "type": "single", "question": "Q2", "options": ["A.x","B.y","C.z","D.w"], "answer": "B"},
        {"id": "q3", "type": "single", "question": "Q3", "options": ["A.1","B.2","C.3","D.4"], "answer": "C"},
        {"id": "q4", "type": "multiple", "question": "Q4", "options": ["A.x","B.y","C.z","D.w"], "answers": ["A","C"]},
        {"id": "q5", "type": "multiple", "question": "Q5", "options": ["A.a","B.b","C.c","D.d"], "answers": ["B","D"]},
        {"id": "q6", "type": "true_false", "question": "Q6", "answer": True},
        {"id": "q7", "type": "true_false", "question": "Q7", "answer": False},
        {"id": "q8", "type": "fill", "question": "Q8", "answer": "hello"},
        {"id": "q9", "type": "fill", "question": "Q9", "answer": "world"},
        {"id": "q10", "type": "match", "question": "Q10", "left":["A","B"], "right":["1","2"], "matches":{"A":"1","B":"2"}},
    ]
}


async def _reg(client: AsyncClient, username: str) -> str:
    await client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@test.com",
        "phone": f"139{hash(username) % 100000000:08d}", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": username, "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _lib(client, token, name=None):
    n = name or unique_library_name("exlib")
    r = await client.post("/api/libraries", json={"name": n, "description": "x"}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _doc(client, token, lib_id, filename="test.md", content=b"# Hello"):
    files = {"file": (filename, content, "text/markdown")}
    r = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {token}"})
    aid = r.json()["data"]["id"]
    await client.post(f"/api/approvals/{aid}/confirm", headers={"Authorization": f"Bearer {token}"})


async def _prompt(client, token, name="ep", ptype="exam"):
    r = await client.post("/api/ai-prompts", json={"name": name, "prompt": "test p", "prompt_type": ptype}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _gen_qb(client) -> tuple[int, str]:
    with patch("app.routers.question_banks.generate_exam", side_effect=lambda *a, **kw: MOCK_QB_DATA):
        token = await _reg(client, "ex_qb_gen")
        lib_id = await _lib(client, token)
        await _doc(client, token, lib_id)
        pid = await _prompt(client, token, "exprompt")
        r = await client.post("/api/question-banks/generate", json={
            "name": f"ex_qb_{hash(lib_id)}", "library_id": lib_id, "document_names": [], "prompt_id": pid,
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 202
        job_id = r.json()["data"]["job_id"]
        for _ in range(200):
            await asyncio.sleep(0.05)
            st = await client.get(f"/api/question-banks/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
            js = st.json()["data"]
            if js.get("status") == "done":
                return js["result"]["id"], token
            if js.get("status") == "failed":
                raise AssertionError(f"generation failed: {js.get('error')}")
        raise AssertionError("generation job timed out")


class TestExamGenerate:
    @pytest.mark.asyncio
    async def test_validate_happy(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        resp = await client.post("/api/exams/generate/validate", json={
            "name": "test", "description": "", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 5}],
            "types": [
                {"type": "single", "count": 2, "score": 10},
                {"type": "multiple", "count": 1, "score": 20},
                {"type": "true_false", "count": 1, "score": 20},
                {"type": "fill", "count": 1, "score": 40},
            ],
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert d["valid"] is True
        assert d["total_score"] == 100

    @pytest.mark.asyncio
    async def test_validate_score_not_100(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        resp = await client.post("/api/exams/generate/validate", json={
            "name": "test", "description": "", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 2}],
            "types": [{"type": "single", "count": 2, "score": 20}],
        }, headers={"Authorization": f"Bearer {token}"})
        d = resp.json()["data"]
        assert d["valid"] is False
        assert any("总分必须为 100" in e for e in d["errors"])

    @pytest.mark.asyncio
    async def test_validate_insufficient_questions(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        resp = await client.post("/api/exams/generate/validate", json={
            "name": "test", "description": "", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "percentage": 100}],
            "types": [{"type": "single", "count": 5, "score": 20}],
        }, headers={"Authorization": f"Bearer {token}"})
        d = resp.json()["data"]
        assert d["valid"] is False
        assert any("不足" in e for e in d["errors"])

    @pytest.mark.asyncio
    async def test_generate_exam(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        resp = await client.post("/api/exams/generate", json={
            "name": "new_exam", "description": "", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 3}],
            "types": [
                {"type": "single", "count": 2, "score": 30},
                {"type": "fill", "count": 1, "score": 40},
            ],
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        d = resp.json()["data"]
        assert d["name"] == "new_exam"
        assert len(d["questions"]) == 3
        assert d["duration_minutes"] == 30


class TestExamCRUD:
    @pytest.mark.asyncio
    async def test_list_update_delete(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        data = {"name": "del_exam", "description": "", "duration_minutes": 30, "pass_score": 60,
                "banks": [{"qb_id": qb_id, "count": 2}],
                "types": [{"type": "single", "count": 1, "score": 50}, {"type": "fill", "count": 1, "score": 50}]}
        r = await client.post("/api/exams/generate", json=data, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]

        resp = await client.get("/api/exams", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["items"]) >= 1

        resp = await client.put(f"/api/exams/{eid}", json={"name": "renamed"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = await client.delete(f"/api/exams/{eid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_paper(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        r = await client.post("/api/exams/generate", json={
            "name": "paper_exam", "description": "", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 2}],
            "types": [{"type": "single", "count": 1, "score": 50}, {"type": "fill", "count": 1, "score": 50}],
        }, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]
        resp = await client.get(f"/api/exams/{eid}/paper", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["questions"]) == 2


class TestExamBatches:
    @pytest.mark.asyncio
    async def test_create_batch_with_students(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        r = await client.post("/api/exams/generate", json={
            "name": "batch_exam", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 2}],
            "types": [{"type": "single", "count": 1, "score": 50}, {"type": "fill", "count": 1, "score": 50}],
        }, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]

        stu_tok = await _reg(client, "ex_batch_stu")
        stu_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {stu_tok}"})
        stu_id = stu_resp.json()["data"]["id"]

        resp = await client.post(f"/api/exams/{eid}/batches", json={
            "name": "第一轮", "description": "", "start_time": None, "end_time": None,
            "duration_minutes": 30, "pass_score": 60,
            "student_ids": [stu_id], "exclude_completed_days": 0,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201

        resp = await client.get(f"/api/exams/{eid}/batches", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["batches"]) >= 1

    @pytest.mark.asyncio
    async def test_batch_delete_without_completed(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        r = await client.post("/api/exams/generate", json={
            "name": "bdel_exam", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 2}],
            "types": [{"type": "single", "count": 1, "score": 50}, {"type": "fill", "count": 1, "score": 50}],
        }, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]
        stu_tok = await _reg(client, "ex_bdel_stu")
        stu_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {stu_tok}"})
        stu_id = stu_resp.json()["data"]["id"]

        br = await client.post(f"/api/exams/{eid}/batches", json={
            "student_ids": [stu_id], "exclude_completed_days": 0,
        }, headers={"Authorization": f"Bearer {token}"})
        bid = br.json()["data"]["id"]

        resp = await client.delete(f"/api/exams/{eid}/batches/{bid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestStudentExam:
    @pytest.mark.asyncio
    async def test_my_lists(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        r = await client.post("/api/exams/generate", json={
            "name": "smy_exam", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 3}],
            "types": [
                {"type": "single", "count": 1, "score": 30},
                {"type": "multiple", "count": 1, "score": 30},
                {"type": "true_false", "count": 1, "score": 40},
            ],
        }, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]

        stu_tok = await _reg(client, "ex_smy_stu")
        stu_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {stu_tok}"})
        stu_id = stu_resp.json()["data"]["id"]

        await client.post(f"/api/exams/{eid}/batches", json={
            "student_ids": [stu_id], "exclude_completed_days": 0,
        }, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/exams/my", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "upcoming" in data
        assert "in_progress" in data
        assert "expired" in data
        assert len(data["in_progress"]) >= 1

    @pytest.mark.asyncio
    async def test_take_and_submit(self, client: AsyncClient):
        qb_id, token = await _gen_qb(client)
        r = await client.post("/api/exams/generate", json={
            "name": "take_exam", "duration_minutes": 30, "pass_score": 60,
            "banks": [{"qb_id": qb_id, "count": 3}],
            "types": [
                {"type": "single", "count": 1, "score": 30},
                {"type": "multiple", "count": 1, "score": 30},
                {"type": "true_false", "count": 1, "score": 40},
            ],
        }, headers={"Authorization": f"Bearer {token}"})
        eid = r.json()["data"]["id"]

        stu_tok = await _reg(client, "ex_take_stu")
        stu_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {stu_tok}"})
        stu_id = stu_resp.json()["data"]["id"]

        await client.post(f"/api/exams/{eid}/batches", json={
            "student_ids": [stu_id], "exclude_completed_days": 0,
        }, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get(f"/api/exams/{eid}/take", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200
        qs = resp.json()["data"]["questions"]
        assert len(qs) == 3

        # submit answers
        ans = []
        for q in qs:
            if q["type"] == "single":
                ans.append({"question_id": q["id"], "answer": "A"})
            elif q["type"] == "multiple":
                ans.append({"question_id": q["id"], "answer": ["A", "C"]})
            elif q["type"] == "true_false":
                ans.append({"question_id": q["id"], "answer": True})
            elif q["type"] == "fill":
                ans.append({"question_id": q["id"], "answer": "test"})
            elif q["type"] == "match":
                ans.append({"question_id": q["id"], "answer": {"A": "1", "B": "2"}})

        resp = await client.post(f"/api/exams/{eid}/submit", json={"answers": ans}, headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200
        sr = resp.json()["data"]
        assert sr["completed"] >= 1

        resp = await client.get(f"/api/exams/{eid}/my-result", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200

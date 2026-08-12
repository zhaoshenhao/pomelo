import pytest
from httpx import AsyncClient
from unittest.mock import patch

from tests.utils import unique_library_name

MOCK_QB_DATA = {
    "questions": [
        {"id": "q1", "type": "single", "question": "单选题", "options": ["A.a", "B.b", "C.c", "D.d"], "answer": "A"},
        {"id": "q2", "type": "single", "question": "单选题2", "options": ["A.x", "B.y", "C.z", "D.w"], "answer": "B"},
        {"id": "q3", "type": "multiple", "question": "多选题", "options": ["A.x", "B.y", "C.z", "D.w"], "answers": ["A","C"]},
        {"id": "q4", "type": "true_false", "question": "对错题", "answer": True},
        {"id": "q5", "type": "fill", "question": "填空", "answer": "hello"},
        {"id": "q6", "type": "match", "question": "匹配", "left":["A","B"], "right":["1","2"], "matches":{"A":"1","B":"2"}},
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
    n = name or unique_library_name("qblib")
    r = await client.post("/api/libraries", json={"name": n, "description": "x"}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _doc(client, token, lib_id, filename="test.md", content=b"# Hello"):
    files = {"file": (filename, content, "text/markdown")}
    r = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {token}"})
    aid = r.json()["data"]["id"]
    await client.post(f"/api/approvals/{aid}/confirm", headers={"Authorization": f"Bearer {token}"})


async def _prompt(client, token, name="qp", ptype="exam"):
    r = await client.post("/api/ai-prompts", json={"name": name, "prompt": "test p", "prompt_type": ptype}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


def _gen_ai(*a, **kw):
    return MOCK_QB_DATA


class TestQBGenerate:
    @pytest.mark.asyncio
    async def test_generate_happy(self, client: AsyncClient):
        with patch("app.routers.question_banks.generate_exam", side_effect=_gen_ai):
            token = await _reg(client, "qbg1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "a.md")
            pid = await _prompt(client, token, "qbprompt1")
            resp = await client.post("/api/question-banks/generate", json={
                "name": "测试题库", "description": "desc", "library_id": lib_id,
                "document_names": ["a.md"], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 202
            job_id = resp.json()["data"]["job_id"]

            # poll until done
            import asyncio
            for _ in range(120):
                await asyncio.sleep(0.5)
                r = await client.get(f"/api/question-banks/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
                job = r.json()["data"]
                if job["status"] == "done":
                    break
                if job["status"] == "failed":
                    raise Exception(job.get("error", "unknown"))

            # verify QB created
            resp = await client.get("/api/question-banks", headers={"Authorization": f"Bearer {token}"})
            items = resp.json()["data"]["items"]
            assert len(items) >= 1
            qb_id = items[0]["id"]

            resp = await client.get(f"/api/question-banks/{qb_id}/paper", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["name"] == "测试题库"
            assert len(data["questions"]) == 6
            assert data["statistics"]["total"] == 6

    @pytest.mark.asyncio
    async def test_generate_duplicate_name(self, client: AsyncClient):
        with patch("app.routers.question_banks.generate_exam", side_effect=_gen_ai):
            token = await _reg(client, "qbg2")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id)
            pid = await _prompt(client, token, "qbprompt2")
            resp = await client.post("/api/question-banks/generate", json={
                "name": "dupq", "description": "", "library_id": lib_id, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 202
            job_id = resp.json()["data"]["job_id"]
            # wait for first job to complete (so the name is taken)
            import asyncio
            for _ in range(60):
                await asyncio.sleep(0.3)
                r = await client.get(f"/api/question-banks/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
                if r.json()["data"]["status"] in ("done", "failed"):
                    break
            # second call should fail on duplicate name
            resp = await client.post("/api/question-banks/generate", json={
                "name": "dupq", "description": "", "library_id": lib_id, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 400


class TestQBList:
    @pytest.mark.asyncio
    async def test_list_paper_update_delete(self, client: AsyncClient):
        with patch("app.routers.question_banks.generate_exam", side_effect=_gen_ai):
            token = await _reg(client, "qbl1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id)
            pid = await _prompt(client, token, "qbprompt3")
            r = await client.post("/api/question-banks/generate", json={
                "name": "qbtest", "description": "x", "library_id": lib_id, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 202
            job_id = r.json()["data"]["job_id"]
            import asyncio
            for _ in range(60):
                await asyncio.sleep(0.3)
                jr = await client.get(f"/api/question-banks/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
                job = jr.json()["data"]
                if job["status"] == "done":
                    break
                if job["status"] == "failed":
                    raise Exception(job.get("error", "unknown"))
            else:
                raise RuntimeError("Job did not complete")

            resp = await client.get("/api/question-banks", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            items = resp.json()["data"]["items"]
            assert len(items) >= 1
            qb_id = items[0]["id"]

            resp = await client.get(f"/api/question-banks/{qb_id}/paper", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert len(resp.json()["data"]["questions"]) == 6

            resp = await client.put(f"/api/question-banks/{qb_id}", json={"name": "renamed"}, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200

            resp = await client.delete(f"/api/question-banks/{qb_id}", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_student_forbidden(self, client: AsyncClient):
        await _reg(client, "qbl2adm")
        stu_tok = await _reg(client, "qbl2stu")
        resp = await client.get("/api/question-banks", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 403

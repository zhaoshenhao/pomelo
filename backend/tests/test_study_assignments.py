import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.models.ai_prompt import AIPrompt
from app.models.document import DocumentLibrary
from app.models.study_material import StudyMaterial
from tests.utils import unique_library_name

MOCK_AI_DATA = {
    "style": ".card{background:#fff}",
    "cover": {"title": "测试封面", "description": "<p>内容</p>", "narration": "朗读"},
    "chapters": [{"title": "第一章", "summary": "<p>摘要</p>", "narration": "朗读", "pages": [{"title": "第一节", "content": "<p>正文</p>", "narration": "第一页朗读文本"}]}],
    "end": {"title": "结束", "content": "<p>感谢</p>", "narration": "结束朗读"},
}


async def _reg(client: AsyncClient, username: str) -> str:
    await client.post("/api/auth/register", json={"username": username, "email": f"{username}@test.com", "phone": f"139{hash(username) % 100000000:08d}", "department": "Dept", "password": "pwd123"})
    resp = await client.post("/api/auth/login", json={"username": username, "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _lib(client, token, name=None):
    n = name or unique_library_name("clib")
    r = await client.post("/api/libraries", json={"name": n, "description": "x"}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _doc(client, token, lib_id, filename="test.md", content=b"# Hello"):
    files = {"file": (filename, content, "text/markdown")}
    r = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {token}"})
    aid = r.json()["data"]["id"]
    await client.post(f"/api/approvals/{aid}/confirm", headers={"Authorization": f"Bearer {token}"})


async def _prompt(client, token, name="sp", ptype="study"):
    r = await client.post("/api/ai-prompts", json={"name": name, "prompt": "test p", "prompt_type": ptype}, headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _gen_mat(client, token):
    with patch("app.routers.study_materials.generate_study_material", side_effect=lambda *a, **kw: MOCK_AI_DATA), \
         patch("app.routers.study_materials.synthesize", side_effect=lambda *a, **kw: 3.0):
        lib_id = await _lib(client, token)
        await _doc(client, token, lib_id, "a.md")
        pid = await _prompt(client, token, "sp_gen", "study")
        r = await client.post("/api/study-materials/generate", json={"name": unique_library_name("sm"), "description": "x", "library_id": lib_id, "document_names": ["a.md"], "prompt_id": pid}, headers={"Authorization": f"Bearer {token}"})
        job_id = r.json()["data"]["job_id"]
        for _ in range(200):
            await asyncio.sleep(0.05)
            st = await client.get(f"/api/study-materials/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
            js = st.json()["data"]
            if js.get("status") == "done":
                return js["material_id"]
            if js.get("status") == "failed":
                raise AssertionError(f"generation failed: {js.get('error')}")
        raise AssertionError("generation job timed out")


class TestStudyAssignment:
    @pytest.mark.asyncio
    async def test_my_all_active(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr1")
        await _gen_mat(client, token)
        stu_tok = await _reg(client, "sa_stu_1")
        resp = await client.get("/api/study-assignments/my", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0]["active"] is True

    @pytest.mark.asyncio
    async def test_inactive_not_visible(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr_inactive")
        mid = await _gen_mat(client, token)
        await client.put(f"/api/study-materials/{mid}", json={"active": False}, headers={"Authorization": f"Bearer {token}"})
        stu_tok = await _reg(client, "sa_stu_inactive")
        resp = await client.get("/api/study-assignments/my", headers={"Authorization": f"Bearer {stu_tok}"})
        items = resp.json()["data"]["items"]
        assert all(i["material_id"] != mid for i in items)

    @pytest.mark.asyncio
    async def test_start_and_page(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr2")
        mid = await _gen_mat(client, token)
        stu_tok = await _reg(client, "sa_stu_2")
        # read_count increments
        resp = await client.get("/api/study-assignments/start", params={"material_id": mid}, headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert len(d["pages"]) > 0
        aid = d["id"]

        # page content
        pf = d["pages"][0]["file"]
        resp = await client.get(f"/api/study-assignments/{aid}/page/{pf}", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 200

        # read_count should be 1 now
        detail = await client.get(f"/api/study-materials/{mid}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["data"]["read_count"] == 1

    @pytest.mark.asyncio
    async def test_progress_and_complete(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr3")
        mid = await _gen_mat(client, token)
        stu_tok = await _reg(client, "sa_stu_3")
        resp = await client.get("/api/study-assignments/start", params={"material_id": mid}, headers={"Authorization": f"Bearer {stu_tok}"})
        aid = resp.json()["data"]["id"]

        await client.post(f"/api/study-assignments/{aid}/progress", json={"seconds": 60}, headers={"Authorization": f"Bearer {stu_tok}"})
        await client.post(f"/api/study-assignments/{aid}/complete", json={"seconds": 120}, headers={"Authorization": f"Bearer {stu_tok}"})

        detail = await client.get(f"/api/study-materials/{mid}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["data"]["complete_count"] >= 1

    @pytest.mark.asyncio
    async def test_min_minutes_auto(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr4")
        mid = await _gen_mat(client, token)
        detail = await client.get(f"/api/study-materials/{mid}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["data"]["min_minutes"] >= 1

    @pytest.mark.asyncio
    async def test_edit_active_min(self, client: AsyncClient):
        token = await _reg(client, "sa_tchr5")
        mid = await _gen_mat(client, token)
        await client.put(f"/api/study-materials/{mid}", json={"active": False, "min_minutes": 15}, headers={"Authorization": f"Bearer {token}"})
        detail = await client.get(f"/api/study-materials/{mid}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["data"]["active"] is False
        assert detail.json()["data"]["min_minutes"] == 15


async def _seed_material(client: AsyncClient, db_session: AsyncSession, token: str) -> int:
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    admin_id = me.json()["data"]["id"]

    lib = DocumentLibrary(name=unique_library_name("lib"), local_path=unique_library_name("ldir"))
    db_session.add(lib)
    await db_session.flush()

    prompt = AIPrompt(name=unique_library_name("prompt"), prompt="x", prompt_type="study")
    db_session.add(prompt)
    await db_session.flush()

    material = StudyMaterial(
        name=unique_library_name("sm"), description="x",
        library_id=lib.id, document_names="", prompt_id=prompt.id,
        created_by=admin_id, min_minutes=10,
    )
    db_session.add(material)
    await db_session.commit()
    return material.id


class TestStudyMaterialSummary:
    @pytest.mark.asyncio
    async def test_summary_not_found(self, client: AsyncClient):
        token = await _reg(client, "sms_tchr_404")
        resp = await client.get("/api/study-materials/999999/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_summary_student_forbidden(self, client: AsyncClient):
        await _reg(client, "sms_tchr_fbd")
        stu_tok = await _reg(client, "sms_stu_fbd")
        resp = await client.get("/api/study-materials/1/summary", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_summary_empty_lists_all_students(self, client: AsyncClient, db_session: AsyncSession):
        token = await _reg(client, "sms_tchr_empty")
        mid = await _seed_material(client, db_session, token)
        await _reg(client, "sms_stu_empty")
        resp = await client.get(f"/api/study-materials/{mid}/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["stats"]["students_viewed"] == 0
        assert data["stats"]["students_completed"] == 0
        assert data["stats"]["total_open_count"] == 0
        assert data["stats"]["total_watch_seconds"] == 0
        assert data["stats"]["avg_watch_seconds"] == 0.0
        names = [s["name"] for s in data["students"]]
        assert "sms_stu_empty" in names
        row = next(s for s in data["students"] if s["name"] == "sms_stu_empty")
        assert row["viewed"] is False
        assert row["completed"] is False
        assert row["read_count"] == 0
        assert row["complete_count"] == 0

    @pytest.mark.asyncio
    async def test_summary_with_progress_and_complete(self, client: AsyncClient, db_session: AsyncSession):
        token = await _reg(client, "sms_tchr1")
        mid = await _seed_material(client, db_session, token)
        stu_tok = await _reg(client, "sms_stu1")
        start = await client.get("/api/study-assignments/start", params={"material_id": mid}, headers={"Authorization": f"Bearer {stu_tok}"})
        aid = start.json()["data"]["id"]
        await client.post(f"/api/study-assignments/{aid}/progress", json={"seconds": 60}, headers={"Authorization": f"Bearer {stu_tok}"})
        await client.post(f"/api/study-assignments/{aid}/complete", json={"seconds": 120}, headers={"Authorization": f"Bearer {stu_tok}"})

        resp = await client.get(f"/api/study-materials/{mid}/summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        stats = data["stats"]
        assert stats["students_viewed"] == 1
        assert stats["students_completed"] == 1
        assert stats["total_open_count"] == 1
        assert stats["total_watch_seconds"] == 180
        assert stats["avg_watch_seconds"] == 180.0

        row = next(s for s in data["students"] if s["name"] == "sms_stu1")
        assert row["viewed"] is True
        assert row["completed"] is True
        assert row["total_study_seconds"] == 180
        assert row["read_count"] == 1
        assert row["complete_count"] == 1

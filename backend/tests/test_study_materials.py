import asyncio

import pytest
from httpx import AsyncClient
from unittest.mock import patch

from tests.utils import unique_library_name

MOCK_AI_DATA = {
    "style": ".card{background:#eef}\n@keyframes fade{from{opacity:0}to{opacity:1}}",
    "cover": {"title": "测试封面", "description": "<p>封面描述内容</p>", "narration": "封面朗读文本"},
    "chapters": [
        {
            "title": "第一章",
            "summary": "<p>第一章摘要</p>",
            "narration": "第一章朗读文本",
            "pages": [
                {"title": "第一节", "content": "<h3>第一节标题</h3><p>第一节内容</p>", "narration": "第一节朗读"},
                {"title": "第二节", "content": "<h3>第二节标题</h3><p>第二节内容</p>", "narration": "第二节朗读"},
            ],
        },
        {
            "title": "第二章",
            "summary": "<p>第二章摘要</p>",
            "narration": "第二章朗读文本",
            "pages": [
                {"title": "第一节", "content": "<h3>第一节</h3><p>内容</p>", "narration": "第一节朗读"},
            ],
        },
    ],
    "end": {"title": "结束", "content": "<p>感谢学习</p>", "narration": "结束朗读文本"},
}


async def _reg(client: AsyncClient, username: str) -> str:
    await client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@test.com",
        "phone": f"139{hash(username) % 100000000:08d}", "department": "Dept",
        "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": username, "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _lib(client, token, name=None):
    n = name or unique_library_name("smlib")
    r = await client.post("/api/libraries", json={"name": n, "description": "x"},
                          headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


async def _doc(client, token, lib_id, filename="test.md", content=b"# Hello"):
    files = {"file": (filename, content, "text/markdown")}
    r = await client.post(f"/api/approvals?library_id={lib_id}", files=files,
                          headers={"Authorization": f"Bearer {token}"})
    aid = r.json()["data"]["id"]
    await client.post(f"/api/approvals/{aid}/confirm", headers={"Authorization": f"Bearer {token}"})


async def _prompt(client, token, name="smp", ptype="study"):
    r = await client.post("/api/ai-prompts", json={"name": name, "prompt": "test p", "prompt_type": ptype},
                          headers={"Authorization": f"Bearer {token}"})
    return r.json()["data"]["id"]


def _gen(*args, **kwargs):
    return MOCK_AI_DATA


async def _fake_synthesize(text, voice, out_path):
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(b"\x00" * 10)
    return 3.0


async def _gen_material(client: AsyncClient, token: str, lib_id: int, pid: int, name: str, doc_names: list) -> int:
    resp = await client.post("/api/study-materials/generate", json={
        "name": name, "description": "x", "library_id": lib_id,
        "document_names": doc_names, "prompt_id": pid,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 202
    job_id = resp.json()["data"]["job_id"]
    for _ in range(200):
        await asyncio.sleep(0.05)
        st = await client.get(f"/api/study-materials/generate/{job_id}", headers={"Authorization": f"Bearer {token}"})
        js = st.json()["data"]
        if js.get("status") == "done":
            return js["material_id"]
        if js.get("status") == "failed":
            raise AssertionError(f"generation failed: {js.get('error')}")
    raise AssertionError("generation job timed out")


class TestStudyMaterialGenerate:
    @pytest.mark.asyncio
    async def test_generate_happy(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_admin1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "a.md")
            await _doc(client, token, lib_id, "b.md")
            pid = await _prompt(client, token, "study_pmt", "study")

            material_id = await _gen_material(client, token, lib_id, pid, "测试资料", ["a.md"])

            resp = await client.get(f"/api/study-materials/{material_id}", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["name"] == "测试资料"
            assert data["library_name"]
            assert data["document_names"] == "a.md"
            assert len(data["pages"]) > 0
            assert data["voice"] == ""

            first_page = data["pages"][0]
            presp = await client.get(
                f"/api/study-materials/{material_id}/page/{first_page['file']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert presp.status_code == 200
            page_html = presp.json()["data"]["html"]
            assert ".card{background:#eef}" in page_html
            assert "@keyframes fade" in page_html

    @pytest.mark.asyncio
    async def test_generate_all_docs(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_genall")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "a.md")
            await _doc(client, token, lib_id, "b.md")
            pid = await _prompt(client, token, "sp2", "study")

            material_id = await _gen_material(client, token, lib_id, pid, "全库", [])
            resp = await client.get(f"/api/study-materials/{material_id}", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert "b.md" in resp.json()["data"]["document_names"]

    @pytest.mark.asyncio
    async def test_invalid_library_404(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_badlib")
            pid = await _prompt(client, token, "sp3", "study")
            resp = await client.post("/api/study-materials/generate", json={
                "name": "x", "library_id": 99999, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_document_404(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_baddoc")
            lib_id = await _lib(client, token)
            pid = await _prompt(client, token, "sp4", "study")
            resp = await client.post("/api/study-materials/generate", json={
                "name": "x", "library_id": lib_id,
                "document_names": ["nonexistent.md"], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_study_prompt_404(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_badpmt")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id)
            rew_id = await _prompt(client, token, "rw_pmt", "rewrite")
            resp = await client.post("/api/study-materials/generate", json={
                "name": "x", "library_id": lib_id, "document_names": [], "prompt_id": rew_id,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_library_no_docs_400(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_emptylib")
            lib_id = await _lib(client, token)
            pid = await _prompt(client, token, "sp5", "study")
            resp = await client.post("/api/study-materials/generate", json={
                "name": "x", "library_id": lib_id, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_student_denied_403(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            admin_tok = await _reg(client, "sm_adm_for_stu")
            lib_id = await _lib(client, admin_tok)
            await _doc(client, admin_tok, lib_id)
            pid = await _prompt(client, admin_tok, "sp6", "study")

            await _reg(client, "sm_adm_gap")
            stu_tok = await _reg(client, "sm_stu")
            resp = await client.post("/api/study-materials/generate", json={
                "name": "x", "library_id": lib_id, "document_names": [], "prompt_id": pid,
            }, headers={"Authorization": f"Bearer {stu_tok}"})
            assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_style_css_sanitized(self, client: AsyncClient):
        bad_style = (
            "@import url('evil.css');\n"
            "body{background:url(http://x.com/track)}\n"
            ".safe{color:red}\n"
            "<script>alert(1)</script>\n"
            "</style>\n"
            "expression(alert(1))\n"
            "javascript:void(0)\n"
        )
        mock_data = dict(MOCK_AI_DATA)
        mock_data["style"] = bad_style

        def _bad_gen(*args, **kwargs):
            return mock_data

        with patch("app.routers.study_materials.generate_study_material", side_effect=_bad_gen):
            token = await _reg(client, "sm_css_san")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id)
            pid = await _prompt(client, token, "sp7", "study")

            material_id = await _gen_material(client, token, lib_id, pid, "san test", [])
            resp = await client.get(f"/api/study-materials/{material_id}", headers={"Authorization": f"Bearer {token}"})
            first_page = resp.json()["data"]["pages"][0]
            presp = await client.get(
                f"/api/study-materials/{material_id}/page/{first_page['file']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            page_html = presp.json()["data"]["html"]
            assert "@import" not in page_html
            assert "url(http" not in page_html
            assert "<script>" not in page_html
            assert "expression" not in page_html
            assert "javascript:" not in page_html
            assert page_html.count("</style>") == 1
            assert ".safe{color:red}" in page_html


class TestStudyMaterialList:
    @pytest.mark.asyncio
    async def test_list_pagination(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_list1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "d0.md")
            pid = await _prompt(client, token, "sp_list0", "study")
            for i in range(3):
                await _gen_material(client, token, lib_id, pid, f"资料_{i}", ["d0.md"])

        resp = await client.get("/api/study-materials", params={"page": 1, "page_size": 2},
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_search(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_search_admin")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "s0.md")
            pid = await _prompt(client, token, "ssp0", "study")
            await _gen_material(client, token, lib_id, pid, "独特资料_搜索测试", ["s0.md"])
            await _gen_material(client, token, lib_id, pid, "普通资料", ["s0.md"])

        resp = await client.get("/api/study-materials", params={"search": "独特资料",
                                "page": 1, "page_size": 10},
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_auth_required(self, client: AsyncClient):
        resp = await client.get("/api/study-materials")
        assert resp.status_code == 401


class TestStudyMaterialDetail:
    @pytest.mark.asyncio
    async def test_detail_and_page(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_detail1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "detail.md")
            pid = await _prompt(client, token, "sp_detail", "study")
            mid = await _gen_material(client, token, lib_id, pid, "详情测试", ["detail.md"])

        resp = await client.get(f"/api/study-materials/{mid}",
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert detail["name"] == "详情测试"
        assert len(detail["pages"]) > 0

        cover_page = next((p for p in detail["pages"] if p["type"] == "cover"), None)
        resp = await client.get(f"/api/study-materials/{mid}/page/{cover_page['file']}",
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        pg = resp.json()["data"]
        assert "<html" in pg["html"] or "<!DOCTYPE" in pg["html"]
        assert pg["text"] == MOCK_AI_DATA["cover"]["narration"]

    @pytest.mark.asyncio
    async def test_detail_not_found(self, client: AsyncClient):
        token = await _reg(client, "sm_det404")
        resp = await client.get("/api/study-materials/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


class TestStudyMaterialMutate:
    @pytest.mark.asyncio
    async def test_update_and_delete(self, client: AsyncClient):
        with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
            token = await _reg(client, "sm_mut1")
            lib_id = await _lib(client, token)
            await _doc(client, token, lib_id, "mut.md")
            pid = await _prompt(client, token, "sp_mut", "study")
            mid = await _gen_material(client, token, lib_id, pid, "待更新", ["mut.md"])

        resp = await client.put(f"/api/study-materials/{mid}", json={"name": "已更新"},
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = await client.delete(f"/api/study-materials/{mid}",
                                   headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = await client.get(f"/api/study-materials/{mid}",
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient):
        token = await _reg(client, "sm_del404")
        resp = await client.delete("/api/study-materials/99999",
                                   headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


class TestStudyMaterialVoice:
    @pytest.mark.asyncio
    async def test_voices_list(self, client: AsyncClient):
        token = await _reg(client, "sm_voices")
        resp = await client.get("/api/study-materials/voices",
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert len(d["voices"]) >= 1

    @pytest.mark.asyncio
    async def test_voice_material(self, client: AsyncClient):
        with patch("app.routers.study_materials.synthesize", side_effect=_fake_synthesize):
            with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
                token = await _reg(client, "sm_voice")
                lib_id = await _lib(client, token)
                await _doc(client, token, lib_id, "v.md")
                pid = await _prompt(client, token, "sp_voice", "study")
                mid = await _gen_material(client, token, lib_id, pid, "配音测试", ["v.md"])

            resp = await client.post(f"/api/study-materials/{mid}/voice", json={
                "voice": "zh-CN-YunxiNeural",
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200

            detail = await client.get(f"/api/study-materials/{mid}",
                                      headers={"Authorization": f"Bearer {token}"})
            assert detail.status_code == 200
            d = detail.json()["data"]
            assert d["voice"] == "zh-CN-YunxiNeural"
            for p in d["pages"]:
                assert p.get("audio_file") is not None
                assert p.get("audio_duration") == 3.0

    @pytest.mark.asyncio
    async def test_voice_invalid_voice_400(self, client: AsyncClient):
        with patch("app.routers.study_materials.synthesize", side_effect=_fake_synthesize):
            with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
                token = await _reg(client, "sm_badvoice")
                lib_id = await _lib(client, token)
                await _doc(client, token, lib_id)
                pid = await _prompt(client, token, "sp_badv", "study")
                mid = await _gen_material(client, token, lib_id, pid, "x", [])

            resp = await client.post(f"/api/study-materials/{mid}/voice", json={
                "voice": "invalid-voice",
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_audio_serving(self, client: AsyncClient):
        with patch("app.routers.study_materials.synthesize", side_effect=_fake_synthesize):
            with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
                token = await _reg(client, "sm_audio")
                lib_id = await _lib(client, token)
                await _doc(client, token, lib_id, "au.md")
                pid = await _prompt(client, token, "sp_audio", "study")
                mid = await _gen_material(client, token, lib_id, pid, "音频测试", ["au.md"])

            # voice first to generate audio
            await client.post(f"/api/study-materials/{mid}/voice", json={
                "voice": "zh-CN-YunxiNeural",
            }, headers={"Authorization": f"Bearer {token}"})

            detail = await client.get(f"/api/study-materials/{mid}",
                                      headers={"Authorization": f"Bearer {token}"})
            audio_file = detail.json()["data"]["pages"][0]["audio_file"]

            resp = await client.get(f"/api/study-materials/{mid}/audio/{audio_file}",
                                    headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            assert resp.headers.get("content-type", "").startswith("audio/")

    @pytest.mark.asyncio
    async def test_audio_not_found_404(self, client: AsyncClient):
        with patch("app.routers.study_materials.synthesize", side_effect=_fake_synthesize):
            with patch("app.routers.study_materials.generate_study_material", side_effect=_gen):
                token = await _reg(client, "sm_audio404")
                lib_id = await _lib(client, token)
                await _doc(client, token, lib_id)
                pid = await _prompt(client, token, "sp_a404", "study")
                mid = await _gen_material(client, token, lib_id, pid, "x", [])

            resp = await client.get(f"/api/study-materials/{mid}/audio/nonexistent.mp3",
                                    headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_audio_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/study-materials/1/audio/cover.mp3")
        assert resp.status_code == 401

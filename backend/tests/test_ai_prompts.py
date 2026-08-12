import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, username: str) -> str:
    await client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@test.com",
        "phone": f"139{hash(username) % 100000000:08d}", "department": "Dept",
        "password": "password123",
    })
    resp = await client.post("/api/auth/login", json={"username": username, "password": "password123"})
    return resp.json()["data"]["access_token"]


class TestAIPromptsCRUD:
    @pytest.mark.asyncio
    async def test_create_and_list(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_admin1")
        resp = await client.post("/api/ai-prompts", json={
            "name": "简洁", "prompt": "请简洁改写", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "简洁"
        assert data["prompt_type"] == "rewrite"

        resp = await client.get("/api/ai-prompts")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_type(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_filter")
        await client.post("/api/ai-prompts", json={
            "name": "改写风格", "prompt": "改写p", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/ai-prompts", json={
            "name": "学习提示", "prompt": "学习p", "prompt_type": "study",
        }, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get("/api/ai-prompts", params={"type": "rewrite"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["prompt_type"] == "rewrite"

    @pytest.mark.asyncio
    async def test_create_duplicate_same_type_fails(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_dup1")
        await client.post("/api/ai-prompts", json={
            "name": "重复名", "prompt": "p1", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.post("/api/ai-prompts", json={
            "name": "重复名", "prompt": "p2", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_same_name_different_type_succeeds(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_diff")
        await client.post("/api/ai-prompts", json={
            "name": "通用名称", "prompt": "p1", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.post("/api/ai-prompts", json={
            "name": "通用名称", "prompt": "p2", "prompt_type": "study",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_update(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_upd")
        resp = await client.post("/api/ai-prompts", json={
            "name": "原名", "prompt": "原prompt", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        pid = resp.json()["data"]["id"]

        resp = await client.put(f"/api/ai-prompts/{pid}", json={
            "name": "新名", "prompt": "新prompt",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "新名"
        assert data["prompt"] == "新prompt"

    @pytest.mark.asyncio
    async def test_update_type_causes_duplicate_in_target_type(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_utype")
        await client.post("/api/ai-prompts", json={
            "name": "目标", "prompt": "p1", "prompt_type": "study",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.post("/api/ai-prompts", json={
            "name": "源", "prompt": "p2", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        pid = resp.json()["data"]["id"]

        resp = await client.put(f"/api/ai-prompts/{pid}", json={
            "name": "目标", "prompt_type": "study",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_delete(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_del")
        resp = await client.post("/api/ai-prompts", json={
            "name": "待删", "prompt": "p", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        pid = resp.json()["data"]["id"]

        resp = await client.delete(f"/api/ai-prompts/{pid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        resp = await client.get("/api/ai-prompts")
        assert len(resp.json()["data"]) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_404d")
        resp = await client.delete("/api/ai-prompts/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_404u")
        resp = await client.put("/api/ai-prompts/99999", json={"name": "x"},
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_admin_cannot_create(self, client: AsyncClient):
        await _register_and_login(client, "pmt_admin_x")
        token = await _register_and_login(client, "pmt_stdnt")
        resp = await client.post("/api/ai-prompts", json={
            "name": "nope", "prompt": "p", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_delete(self, client: AsyncClient):
        admin_token = await _register_and_login(client, "pmt_admin2")
        resp = await client.post("/api/ai-prompts", json={
            "name": "forbid", "prompt": "p", "prompt_type": "rewrite",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        pid = resp.json()["data"]["id"]

        await _register_and_login(client, "pmt_admin_y")
        stu_token = await _register_and_login(client, "pmt_stu2")
        resp = await client.delete(f"/api/ai-prompts/{pid}", headers={"Authorization": f"Bearer {stu_token}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_prompt_type_returns_error(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_bad")
        resp = await client.post("/api/ai-prompts", json={
            "name": "bad", "prompt": "p", "prompt_type": "unknown",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_without_type_returns_error(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_notype")
        resp = await client.post("/api/ai-prompts", json={
            "name": "notype", "prompt": "p",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_public_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/api/ai-prompts")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_all_three_types(self, client: AsyncClient):
        token = await _register_and_login(client, "pmt_all")
        for t in ("rewrite", "study", "exam"):
            resp = await client.post("/api/ai-prompts", json={
                "name": f"name_{t}", "prompt": f"prompt_{t}", "prompt_type": t,
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 201

        resp = await client.get("/api/ai-prompts")
        data = resp.json()["data"]
        assert len(data) == 3
        types = {p["prompt_type"] for p in data}
        assert types == {"rewrite", "study", "exam"}

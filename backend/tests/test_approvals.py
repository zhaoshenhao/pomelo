import pytest
from httpx import AsyncClient

from tests.utils import unique_library_name


async def _create_approval(client: AsyncClient, admin_token: str, lib_id: int) -> int:
    files = {"file": ("test.md", b"# Hello", "text/markdown")}
    resp = await client.post(
        f"/api/approvals?library_id={lib_id}",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return resp.json()["data"]["id"]


async def _register_admin(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "ac_admin", "email": "ac_admin@test.com",
        "phone": "13900000001", "department": "Dept", "password": "admin123",
    })
    resp = await client.post("/api/auth/login", json={"username": "ac_admin", "password": "admin123"})
    return resp.json()["data"]["access_token"]


async def _create_library(client: AsyncClient, admin_token: str) -> int:
    name = unique_library_name("aclib")
    resp = await client.post("/api/libraries", json={"name": name, "description": "Test"},
                             headers={"Authorization": f"Bearer {admin_token}"})
    return resp.json()["data"]["id"]


async def _add_document_to_library(client: AsyncClient, admin_token: str, lib_id: int) -> int:
    approval_id = await _create_approval(client, admin_token, lib_id)
    await client.post(f"/api/approvals/{approval_id}/confirm",
                      headers={"Authorization": f"Bearer {admin_token}"})
    return approval_id


class TestApprovalContentChoice:
    @pytest.mark.asyncio
    async def test_add_new_empty_library_succeeds(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "新增"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replace_whole_library_empty_fails(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "替换整个文档库"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_replace_partial_empty_fails(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "替换部分文档"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_replace_works_with_docs(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        await _add_document_to_library(client, admin_token, lib_id)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "替换整个文档库"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replace_partial_works_with_docs(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        await _add_document_to_library(client, admin_token, lib_id)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "替换部分文档"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_content_choice_fails(self, client: AsyncClient):
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "invalid_choice"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400


class TestConfirmSameNameReplacement:
    async def _setup_library_with_doc(self, client: AsyncClient) -> tuple[str, int, str]:
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        await _add_document_to_library(client, admin_token, lib_id)
        return admin_token, lib_id, "test.md"

    @pytest.mark.asyncio
    async def test_replace_whole_library_allows_same_name(self, client: AsyncClient):
        admin_token, lib_id, doc_name = await self._setup_library_with_doc(client)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={"content_choice": "替换整个文档库", "new_name": doc_name},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        resp = await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replace_partial_allows_same_name_if_selected(self, client: AsyncClient):
        admin_token, lib_id, doc_name = await self._setup_library_with_doc(client)
        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={
                "content_choice": "替换部分文档",
                "replace_docs": [doc_name],
                "new_name": doc_name,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        resp = await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replace_partial_rejects_same_name_if_not_selected(self, client: AsyncClient):
        admin_token, lib_id, doc_name = await self._setup_library_with_doc(client)
        second_doc_name = "other.md"
        files = {"file": ("other.md", b"# Other", "text/markdown")}
        resp = await client.post(
            f"/api/approvals?library_id={lib_id}",
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        second_approval_id = resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{second_approval_id}/confirm",
                          headers={"Authorization": f"Bearer {admin_token}"})

        approval_id = await _create_approval(client, admin_token, lib_id)

        resp = await client.put(
            f"/api/approvals/{approval_id}/meta",
            json={
                "content_choice": "替换部分文档",
                "replace_docs": [second_doc_name],
                "new_name": doc_name,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        resp = await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

        resp = await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409


class TestRewriteEndpoint:
    async def _setup(self, client: AsyncClient) -> tuple[str, int, int]:
        admin_token = await _register_admin(client)
        lib_id = await _create_library(client, admin_token)
        approval_id = await _create_approval(client, admin_token, lib_id)
        return admin_token, lib_id, approval_id

    @pytest.mark.asyncio
    async def test_rewrite_style_id_missing_400(self, client: AsyncClient):
        admin_token, _, approval_id = await self._setup(client)
        resp = await client.post(
            f"/api/approvals/{approval_id}/rewrite",
            json={"method": "style"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rewrite_style_id_not_found_404(self, client: AsyncClient):
        admin_token, _, approval_id = await self._setup(client)
        resp = await client.post(
            f"/api/approvals/{approval_id}/rewrite",
            json={"method": "style", "style_id": 99999},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rewrite_style_id_wrong_type_not_found(self, client: AsyncClient):
        admin_token, _, approval_id = await self._setup(client)
        resp = await client.post("/api/ai-prompts", json={
            "name": "study-prompt", "prompt": "learn", "prompt_type": "study",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        study_id = resp.json()["data"]["id"]

        resp = await client.post(
            f"/api/approvals/{approval_id}/rewrite",
            json={"method": "style", "style_id": study_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rewrite_invalid_method_400(self, client: AsyncClient):
        admin_token, _, approval_id = await self._setup(client)
        resp = await client.post(
            f"/api/approvals/{approval_id}/rewrite",
            json={"method": "invalid"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

import pytest
from httpx import AsyncClient

from tests.utils import unique_library_name


async def _register_login(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register",
        json={
            "username": "backup_admin",
            "email": "backup@test.com",
            "phone": "13900000001",
            "department": "dept",
            "password": "admin123",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "backup_admin", "password": "admin123"},
    )
    return resp.json()["data"]["access_token"]


async def _add_doc_to_library(client: AsyncClient, token: str, lib_id: int, filename: str, content: bytes) -> int:
    files = {"file": (filename, content, "text/markdown")}
    resp = await client.post(
        f"/api/approvals?library_id={lib_id}", files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    approval_id = resp.json()["data"]["id"]
    await client.post(
        f"/api/approvals/{approval_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    return approval_id


class TestBackupEndpoints:
    @pytest.mark.asyncio
    async def test_list_backups_empty(self, client: AsyncClient):
        token = await _register_login(client)
        lib_name = unique_library_name("empty_lib")
        resp = await client.post(
            "/api/libraries",
            json={"name": lib_name, "description": "desc"},
            headers={"Authorization": f"Bearer {token}"},
        )
        lib_id = resp.json()["data"]["id"]
        resp = await client.get(
            f"/api/libraries/{lib_id}/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_list_backups(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        backups = resp.json()["data"]
        assert len(backups) >= 1
        assert "filename" in backups[0]
        assert "size" in backups[0]
        assert "created_at" in backups[0]

    @pytest.mark.asyncio
    async def test_list_backup_documents(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        backup = resp.json()["data"][-1]
        backup_filename = backup["filename"]

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups/{backup_filename}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        docs = resp.json()["data"]
        assert len(docs) >= 1
        assert docs[0]["name"] == "first_doc.md"

    @pytest.mark.asyncio
    async def test_get_backup_document_content(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        backup = resp.json()["data"][-1]
        backup_filename = backup["filename"]

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups/{backup_filename}/documents/first_doc.md/content",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["content"] == "# First Document"

    @pytest.mark.asyncio
    async def test_restore_backup(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.get(
            f"/api/libraries/{lib_id}/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        backup = resp.json()["data"][-1]
        backup_filename = backup["filename"]

        resp = await client.post(
            f"/api/libraries/{lib_id}/backups/{backup_filename}/restore",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        resp = await client.get(
            f"/api/libraries/{lib_id}/documents",
        )
        assert resp.status_code == 200
        docs = resp.json()["data"]["items"]
        assert len(docs) == 1
        assert docs[0]["filename"] == "first_doc.md"

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.post(
            f"/api/libraries/{lib_id}/backups/nonexistent.zip/restore",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_backups_require_auth(self, client: AsyncClient):
        token = await _register_login(client)
        lib_id = await self._setup_library_with_two_docs(client, token)

        resp = await client.get(f"/api/libraries/{lib_id}/backups")
        assert resp.status_code == 401

    async def _setup_library_with_two_docs(self, client: AsyncClient, token: str) -> int:
        lib_name = unique_library_name("backup_test_lib")
        resp = await client.post(
            "/api/libraries",
            json={"name": lib_name, "description": "backup test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        lib_id = resp.json()["data"]["id"]

        await _add_doc_to_library(client, token, lib_id, "first_doc.md", b"# First Document")
        await _add_doc_to_library(client, token, lib_id, "second_doc.md", b"# Second Document")

        return lib_id

import os

import pytest
from httpx import AsyncClient

from tests.utils import unique_library_name


async def register_and_login_teacher(client: AsyncClient) -> tuple[str, str]:
    await client.post("/api/auth/register", json={"username": "t_admin", "email": "ta@test.com", "phone": "13800000001", "department": "TestDept", "password": "admin123"})
    resp = await client.post("/api/auth/login", json={"username": "t_admin", "password": "admin123"})
    admin_token = resp.json()["data"]["access_token"]
    await client.post("/api/auth/register", json={"username": "t_teacher", "email": "tt@test.com", "phone": "13800000002", "department": "TeachDept", "password": "teach123"})
    await client.patch("/api/users/2/role", json={"role": "teacher"}, headers={"Authorization": f"Bearer {admin_token}"})
    resp2 = await client.post("/api/auth/login", json={"username": "t_teacher", "password": "teach123"})
    teacher_token = resp2.json()["data"]["access_token"]
    return admin_token, teacher_token


async def create_library(client: AsyncClient, admin_token: str, name: str = "") -> int:
    lib_name = name or unique_library_name("doclib")
    resp = await client.post("/api/libraries", json={"name": lib_name, "description": "Test"}, headers={"Authorization": f"Bearer {admin_token}"})
    return resp.json()["data"]["id"]


class TestDocumentUpload:
    @pytest.mark.asyncio
    async def test_upload_as_teacher(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("test.md", b"# Hello world", "text/markdown")}
        resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 201
        assert resp.json()["data"]["original_filename"] == "test.md"

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("test.exe", b"binary", "application/octet-stream")}
        resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_path_traversal_filename_rejected(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("..", b"# malicious", "text/markdown")}
        resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("doc1.md", b"# Doc 1", "text/markdown")}
        approval_resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{approval_id}/confirm", headers={"Authorization": f"Bearer {teacher_token}"})
        resp = await client.get(f"/api/libraries/{lib_id}/documents")
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_upload_xlsx(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        from openpyxl import Workbook
        from io import BytesIO
        wb = Workbook()
        ws = wb.active
        ws.title = "Test"
        ws.append(["Header"])
        ws.append(["Value"])
        buf = BytesIO()
        wb.save(buf)
        wb.close()
        buf.seek(0)
        files = {"file": ("data.xlsx", buf.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_deletes_file(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("to_delete.md", b"# Delete me", "text/markdown")}
        approval_resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{approval_id}/confirm", headers={"Authorization": f"Bearer {teacher_token}"})
        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc = list_resp.json()["data"]["items"][0]
        doc_id = doc["id"]
        doc_path = doc["path"]
        assert os.path.exists(doc_path)
        resp = await client.delete(f"/api/libraries/documents/{doc_id}", headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 200
        assert not os.path.exists(doc_path)

    @pytest.mark.asyncio
    async def test_delete_document_unauthenticated(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("no_auth.md", b"# No auth", "text/markdown")}
        approval_resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{approval_id}/confirm", headers={"Authorization": f"Bearer {teacher_token}"})
        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc_id = list_resp.json()["data"]["items"][0]["id"]
        resp = await client.delete(f"/api/libraries/documents/{doc_id}")
        assert resp.status_code == 401


class TestDocumentContentUpdate:
    @pytest.mark.asyncio
    async def test_update_document_content(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("doc.md", b"# Original", "text/markdown")}
        approval_resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{approval_id}/confirm", headers={"Authorization": f"Bearer {teacher_token}"})
        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc_id = list_resp.json()["data"]["items"][0]["id"]

        new_content = "# Updated document content"
        put_resp = await client.put(
            f"/api/libraries/documents/{doc_id}/content",
            json={"content": new_content},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["data"]["content"] == new_content

        get_resp = await client.get(f"/api/libraries/documents/{doc_id}/content")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["content"] == new_content

    @pytest.mark.asyncio
    async def test_update_document_content_unauthorized(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        lib_id = await create_library(client, admin_token)
        files = {"file": ("doc.md", b"# Original", "text/markdown")}
        approval_resp = await client.post(f"/api/approvals?library_id={lib_id}", files=files, headers={"Authorization": f"Bearer {teacher_token}"})
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(f"/api/approvals/{approval_id}/confirm", headers={"Authorization": f"Bearer {teacher_token}"})
        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc_id = list_resp.json()["data"]["items"][0]["id"]

        resp = await client.put(
            f"/api/libraries/documents/{doc_id}/content",
            json={"content": "# Should fail"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_document_content_not_found(self, client: AsyncClient):
        admin_token, teacher_token = await register_and_login_teacher(client)
        resp = await client.put(
            "/api/libraries/documents/99999/content",
            json={"content": "# Missing"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 404

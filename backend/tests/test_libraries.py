import os
import shutil

import pytest
from httpx import AsyncClient

from app.services.file_service import get_library_root, get_library_path
from tests.utils import unique_library_name


async def register_and_login_admin(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register",
        json={"username": "admin_test", "email": "admin@test.com", "phone": "13800000001", "department": "测试部", "password": "admin123"},
    )
    resp = await client.post("/api/auth/login", json={"username": "admin_test", "password": "admin123"})
    return resp.json()["data"]["access_token"]


class TestDocumentLibraryCRUD:
    @pytest.mark.asyncio
    async def test_create_library(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("测试库")
        response = await client.post(
            "/api/libraries",
            json={"name": lib_name, "description": "一个测试文档库"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["name"] == lib_name

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("dup_lib")
        await client.post("/api/libraries", json={"name": lib_name, "description": "test"}, headers={"Authorization": f"Bearer {token}"})
        resp = await client.post("/api/libraries", json={"name": lib_name, "description": "test"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_libraries(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("lib")
        await client.post("/api/libraries", json={"name": lib_name, "description": "a"}, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get("/api/libraries")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    @pytest.mark.asyncio
    async def test_update_library(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        old_name = unique_library_name("old")
        create_resp = await client.post("/api/libraries", json={"name": old_name, "description": "desc"}, headers={"Authorization": f"Bearer {token}"})
        lib_id = create_resp.json()["data"]["id"]
        resp = await client.put(f"/api/libraries/{lib_id}", json={"name": "new_name"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "new_name"

    @pytest.mark.asyncio
    async def test_delete_library(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("to_delete")
        create_resp = await client.post("/api/libraries", json={"name": lib_name, "description": "x"}, headers={"Authorization": f"Bearer {token}"})
        lib_id = create_resp.json()["data"]["id"]
        resp = await client.delete(f"/api/libraries/{lib_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        resp = await client.delete("/api/libraries/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_non_admin_denied(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        await client.post("/api/auth/register", json={"username": "teacher1", "email": "t@test.com", "phone": "111", "department": "d", "password": "pw123"})
        await client.patch("/api/users/2/role", json={"role": "teacher"}, headers={"Authorization": f"Bearer {token}"})
        login_resp = await client.post("/api/auth/login", json={"username": "teacher1", "password": "pw123"})
        teacher_token = login_resp.json()["data"]["access_token"]
        resp = await client.post("/api/libraries", json={"name": "no_perm", "description": "x"}, headers={"Authorization": f"Bearer {teacher_token}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_library_custom_directory(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        dir_name = unique_library_name("test_custom_dir")
        dir_path = os.path.join(get_library_root(), dir_name)
        try:
            resp = await client.post(
                "/api/libraries",
                json={"name": "自定义目录库", "description": "desc", "directory": dir_name},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert data["name"] == "自定义目录库"
            assert dir_name in data["local_path"]
            assert os.path.isdir(dir_path)
        finally:
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)

    @pytest.mark.asyncio
    async def test_create_library_default_directory_same_as_name(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("test_default_dir")
        dir_path = os.path.join(get_library_root(), lib_name)
        try:
            resp = await client.post(
                "/api/libraries",
                json={"name": lib_name, "description": "desc"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert lib_name in data["local_path"]
            assert os.path.isdir(dir_path)
        finally:
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)

    @pytest.mark.asyncio
    async def test_create_library_directory_exists_conflict(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        dir_name = unique_library_name("test_conflict_dir")
        dir_path = os.path.join(get_library_root(), dir_name)
        try:
            get_library_path(dir_name)
            resp = await client.post(
                "/api/libraries",
                json={"name": "冲突库", "description": "desc", "directory": dir_name},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 409
            assert "已存在" in resp.json()["detail"]
        finally:
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)

    @pytest.mark.asyncio
    async def test_create_library_directory_exists_use_existing(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        dir_name = unique_library_name("test_reuse_dir")
        dir_path = os.path.join(get_library_root(), dir_name)
        try:
            get_library_path(dir_name)
            resp = await client.post(
                "/api/libraries",
                json={"name": "复用库", "description": "desc", "directory": dir_name, "use_existing_directory": True},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()["data"]
            assert dir_name in data["local_path"]
        finally:
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)

    @pytest.mark.asyncio
    async def test_create_library_invalid_directory(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        resp = await client.post(
            "/api/libraries",
            json={"name": "bad", "description": "desc", "directory": "../evil"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_force_delete_corrupted_library(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("corrupt_lib")
        create_resp = await client.post(
            "/api/libraries",
            json={"name": lib_name, "description": "test", "directory": lib_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        lib_id = create_resp.json()["data"]["id"]

        files = {"file": ("corrupt.md", b"# Corrupt test", "text/markdown")}
        approval_resp = await client.post(
            f"/api/approvals?library_id={lib_id}", files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )

        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc = list_resp.json()["data"]["items"][0]
        doc_path = doc["path"]
        assert os.path.exists(doc_path)
        os.remove(doc_path)
        os.makedirs(doc_path)

        resp = await client.delete(
            f"/api/libraries/{lib_id}?force=true&delete_directory=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        get_resp = await client.get(f"/api/libraries/{lib_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_normal_delete_corrupted_library_fails(self, client: AsyncClient):
        token = await register_and_login_admin(client)
        lib_name = unique_library_name("corrupt_fail")
        create_resp = await client.post(
            "/api/libraries",
            json={"name": lib_name, "description": "test", "directory": lib_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        lib_id = create_resp.json()["data"]["id"]

        files = {"file": ("corrupt2.md", b"# Corrupt fail", "text/markdown")}
        approval_resp = await client.post(
            f"/api/approvals?library_id={lib_id}", files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        approval_id = approval_resp.json()["data"]["id"]
        await client.post(
            f"/api/approvals/{approval_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )

        list_resp = await client.get(f"/api/libraries/{lib_id}/documents")
        doc = list_resp.json()["data"]["items"][0]
        doc_path = doc["path"]
        os.remove(doc_path)
        os.makedirs(doc_path)

        try:
            await client.delete(
                f"/api/libraries/{lib_id}?delete_directory=true",
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception:
            pass

        get_resp = await client.get(f"/api/libraries/{lib_id}")
        assert get_resp.status_code == 200

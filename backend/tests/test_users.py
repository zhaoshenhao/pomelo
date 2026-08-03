import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient, username: str, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "phone": "13800138000", "department": "技术部", "password": "password123"},
    )
    resp = await client.post("/api/auth/login", json={"username": username, "password": "password123"})
    return resp.json()["data"]["access_token"]


class TestUserList:
    @pytest.mark.asyncio
    async def test_list_as_admin(self, client: AsyncClient):
        token = await register_and_login(client, "admin1", "admin1@example.com")
        response = await client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_as_student_denied(self, client: AsyncClient):
        await register_and_login(client, "admin2", "admin2@example.com")
        await client.post(
            "/api/auth/register",
            json={"username": "stu1", "email": "stu1@example.com", "phone": "13800000001", "department": "学习部", "password": "password123"},
        )
        resp = await client.post("/api/auth/login", json={"username": "stu1", "password": "password123"})
        student_token = resp.json()["data"]["access_token"]
        response = await client.get("/api/users", headers={"Authorization": f"Bearer {student_token}"})
        assert response.status_code == 403


class TestUserRole:
    @pytest.mark.asyncio
    async def test_update_role_as_admin(self, client: AsyncClient):
        admin_token = await register_and_login(client, "admin3", "admin3@example.com")
        await client.post(
            "/api/auth/register",
            json={"username": "stu2", "email": "stu2@example.com", "phone": "13800000002", "department": "学习部", "password": "password123"},
        )
        resp = await client.post("/api/auth/login", json={"username": "stu2", "password": "password123"})
        user_id = resp.json()["data"]["user"]["id"]

        response = await client.patch(
            f"/api/users/{user_id}/role",
            json={"role": "teacher"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["role"] == "teacher"

    @pytest.mark.asyncio
    async def test_update_role_invalid_role(self, client: AsyncClient):
        admin_token = await register_and_login(client, "admin4", "admin4@example.com")
        response = await client.patch(
            "/api/users/1/role",
            json={"role": "superadmin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_role_non_admin(self, client: AsyncClient):
        await register_and_login(client, "admin5", "admin5@example.com")
        await client.post(
            "/api/auth/register",
            json={"username": "stu3", "email": "stu3@example.com", "phone": "13800000003", "department": "学习部", "password": "password123"},
        )
        resp = await client.post("/api/auth/login", json={"username": "stu3", "password": "password123"})
        student_token = resp.json()["data"]["access_token"]
        response = await client.patch(
            "/api/users/1/role",
            json={"role": "teacher"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 403


class TestUserDelete:
    @pytest.mark.asyncio
    async def test_delete_user_as_admin(self, client: AsyncClient):
        admin_token = await register_and_login(client, "admin6", "admin6@example.com")
        await client.post(
            "/api/auth/register",
            json={"username": "todel", "email": "todel@example.com", "phone": "13800000004", "department": "学习部", "password": "password123"},
        )
        resp = await client.post("/api/auth/login", json={"username": "todel", "password": "password123"})
        user_id = resp.json()["data"]["user"]["id"]

        response = await client.delete(f"/api/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_self_denied(self, client: AsyncClient):
        admin_token = await register_and_login(client, "admin7", "admin7@example.com")
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        user_id = resp.json()["data"]["id"]

        response = await client.delete(f"/api/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client: AsyncClient):
        admin_token = await register_and_login(client, "admin8", "admin8@example.com")
        response = await client.delete("/api/users/999999", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404

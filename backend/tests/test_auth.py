import pytest
from httpx import AsyncClient


class TestAuthRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "phone": "13800138000",
                "department": "技术部",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["username"] == "testuser"
        assert data["data"]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "dup", "email": "a@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"},
        )
        response = await client.post(
            "/api/auth/register",
            json={"username": "dup", "email": "b@example.com", "phone": "13800138001", "department": "技术部", "password": "password123"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "user1", "email": "dup@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"},
        )
        response = await client.post(
            "/api/auth/register",
            json={"username": "user2", "email": "dup@example.com", "phone": "13800138001", "department": "技术部", "password": "password123"},
        )
        assert response.status_code == 409


class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "loginuser", "email": "login@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"},
        )
        response = await client.post("/api/auth/login", json={"username": "loginuser", "password": "password123"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "pwduser", "email": "pwd@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"},
        )
        response = await client.post("/api/auth/login", json={"username": "pwduser", "password": "wrong"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/api/auth/login", json={"username": "nobody", "password": "password123"})
        assert response.status_code == 401


class TestAuthMe:
    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, client: AsyncClient):
        await client.post(
            "/api/auth/register",
            json={"username": "meuser", "email": "me@example.com", "phone": "13800138000", "department": "技术部", "password": "password123"},
        )
        login_resp = await client.post("/api/auth/login", json={"username": "meuser", "password": "password123"})
        token = login_resp.json()["data"]["access_token"]
        response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["data"]["username"] == "meuser"

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.config import settings


@pytest_asyncio.fixture(autouse=True)
async def _enable_redis_for_tests():
    original_host = settings.REDIS_HOST
    original_port = settings.REDIS_PORT
    original_password = settings.REDIS_PASSWORD
    settings.REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
    settings.REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", "6380"))
    settings.REDIS_PASSWORD = os.getenv("TEST_REDIS_PASSWORD", "")
    from app.services import redis_store

    redis_store._redis_available = None
    redis_store._redis_client = None

    from app.services.redis_store import _check_redis

    available = await _check_redis()
    if not available:
        settings.REDIS_HOST = original_host
        settings.REDIS_PORT = original_port
        settings.REDIS_PASSWORD = original_password
        redis_store._redis_available = None
        redis_store._redis_client = None
        pytest.skip("Redis not available")
        return

    yield

    settings.REDIS_HOST = original_host
    settings.REDIS_PORT = original_port
    settings.REDIS_PASSWORD = original_password
    redis_store._redis_available = None
    redis_store._redis_client = None


def unique_username():
    import uuid

    return f"sess_{uuid.uuid4().hex[:8]}"


async def register_and_login(client: AsyncClient, username: str):
    await client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "phone": "13800000000",
            "password": "password123",
        },
    )
    resp = await client.post("/api/auth/login", json={"username": username, "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    return data["access_token"], data["refresh_token"]


@pytest.mark.asyncio
class TestRedisSession:
    async def test_login_creates_session(self, client: AsyncClient):
        username = unique_username()
        access_token, refresh_token = await register_and_login(client, username)
        assert access_token

        from app.dependencies.auth import decode_token
        from app.services.redis_store import get_session

        payload = decode_token(access_token)
        assert payload is not None
        jti = payload.get("jti")
        assert jti

        session = await get_session(jti)
        assert session is not None
        assert "user_id" in session

    async def test_session_validates_request(self, client: AsyncClient):
        username = unique_username()
        access_token, _ = await register_and_login(client, username)

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == username

    async def test_logout_deletes_session(self, client: AsyncClient):
        username = unique_username()
        access_token, _ = await register_and_login(client, username)

        from app.dependencies.auth import decode_token

        payload = decode_token(access_token)
        jti = payload["jti"]

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.post("/api/auth/logout", headers=headers)
        assert resp.status_code == 200

        from app.services.redis_store import get_session

        session = await get_session(jti)
        assert session is None

    async def test_expired_session_returns_401(self, client: AsyncClient):
        username = unique_username()
        access_token, _ = await register_and_login(client, username)

        from app.dependencies.auth import decode_token
        from app.services.redis_store import delete_session

        payload = decode_token(access_token)
        jti = payload["jti"]
        await delete_session(jti)

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    async def test_refresh_rotates_session(self, client: AsyncClient):
        username = unique_username()
        access_token, refresh_token = await register_and_login(client, username)

        from app.dependencies.auth import decode_token

        old_payload = decode_token(access_token)
        old_jti = old_payload["jti"]

        resp = await client.post(
            "/api/auth/refresh",
            json={"access_token": access_token, "refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        new_tokens = resp.json()["data"]
        new_access = new_tokens["access_token"]
        new_refresh = new_tokens["refresh_token"]
        assert new_access != access_token
        assert new_refresh != refresh_token

        new_payload = decode_token(new_access)
        new_jti = new_payload["jti"]
        assert new_jti != old_jti

        from app.services.redis_store import get_session

        old_session = await get_session(old_jti)
        assert old_session is None

        new_session = await get_session(new_jti)
        assert new_session is not None

    async def test_refresh_replay_detection(self, client: AsyncClient):
        username = unique_username()
        access_token, refresh_token = await register_and_login(client, username)

        resp1 = await client.post(
            "/api/auth/refresh",
            json={"access_token": access_token, "refresh_token": refresh_token},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            "/api/auth/refresh",
            json={"access_token": access_token, "refresh_token": refresh_token},
        )
        assert resp2.status_code == 401

    async def test_change_password_revokes_sessions(self, client: AsyncClient):
        username = unique_username()
        access_token, _ = await register_and_login(client, username)

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.post(
            "/api/auth/change-password",
            json={"old_password": "password123", "new_password": "newpass456"},
            headers=headers,
        )
        assert resp.status_code == 200

        resp2 = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "password123"},
        )
        assert resp2.status_code == 401

        resp3 = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "newpass456"},
        )
        assert resp3.status_code == 200

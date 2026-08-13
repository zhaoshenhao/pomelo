import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department


class TestEagerDefaults:
    """server_default columns (created_at/updated_at) must be populated right
    after commit, even without an explicit refresh — otherwise accessing them
    in async code triggers a MissingGreenlet lazy-load on MySQL 5.7 (no RETURNING).
    """

    @pytest.mark.asyncio
    async def test_created_at_populated_after_commit(self, db_session: AsyncSession):
        dept = Department(name="eager_d")
        db_session.add(dept)
        await db_session.commit()
        assert dept.created_at is not None
        assert dept.updated_at is not None

    @pytest.mark.asyncio
    async def test_onupdate_populated_after_update_commit(self, db_session: AsyncSession):
        dept = Department(name="eager_d2")
        db_session.add(dept)
        await db_session.commit()
        dept.name = "eager_d2_renamed"
        await db_session.commit()
        assert dept.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_department_via_api(self, client: AsyncClient):
        await client.post("/api/auth/register", json={
            "username": "eager_admin", "email": "eager_admin@test.com",
            "phone": "13900009999", "department": "Dept", "password": "pwd123",
        })
        resp = await client.post("/api/auth/login", json={"username": "eager_admin", "password": "pwd123"})
        token = resp.json()["data"]["access_token"]
        r = await client.post("/api/departments", json={"name": "eager_dept", "description": "x"},
                              headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 201
        assert r.json()["data"]["created_at"]

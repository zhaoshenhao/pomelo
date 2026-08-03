import pytest
from httpx import AsyncClient


async def register_and_login(client: AsyncClient, username: str, email: str, role: str = "admin") -> str:
    resp = await client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "phone": "13800138000", "password": "password123"},
    )
    if resp.status_code == 201:
        data = resp.json()["data"]
        if data.get("role") != role:
            pass
    resp = await client.post("/api/auth/login", json={"username": username, "password": "password123"})
    return resp.json()["data"]["access_token"]


class TestDepartmentCRUD:
    @pytest.mark.asyncio
    async def test_create_department(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin1", "dept_admin1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/departments", json={"name": "技术部"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "技术部"

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin2", "dept_admin2@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/departments", json={"name": "财务部"}, headers=headers)
        resp = await client.post("/api/departments", json={"name": "财务部"}, headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_departments(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin3", "dept_admin3@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/departments", json={"name": "人力资源"}, headers=headers)

        resp = await client.get("/api/departments", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_update_department(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin4", "dept_admin4@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post("/api/departments", json={"name": "old"}, headers=headers)
        dept_id = created.json()["data"]["id"]

        resp = await client.patch(f"/api/departments/{dept_id}", json={"name": "new"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "new"

    @pytest.mark.asyncio
    async def test_delete_department_without_users(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin5", "dept_admin5@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post("/api/departments", json={"name": "empty"}, headers=headers)
        dept_id = created.json()["data"]["id"]

        resp = await client.delete(f"/api/departments/{dept_id}", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_department_with_users(self, client: AsyncClient):
        token = await register_and_login(client, "dept_admin6", "dept_admin6@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post("/api/departments", json={"name": "inuse"}, headers=headers)
        dept_id = created.json()["data"]["id"]

        await client.post(
            "/api/auth/register",
            json={"username": "dept_user", "email": "dept_user@example.com", "phone": "13800000001", "department_id": dept_id, "password": "password123"},
        )

        resp = await client.delete(f"/api/departments/{dept_id}", headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_non_admin_create_denied(self, client: AsyncClient):
        await register_and_login(client, "dept_admin7", "dept_admin7@example.com")
        await client.post("/api/auth/register", json={"username": "stu_dept", "email": "stu_dept@example.com", "phone": "13800000002", "password": "password123"})
        resp = await client.post("/api/auth/login", json={"username": "stu_dept", "password": "password123"})
        stu_token = resp.json()["data"]["access_token"]

        resp = await client.post("/api/departments", json={"name": "hack"}, headers={"Authorization": f"Bearer {stu_token}"})
        assert resp.status_code == 403


class TestUserSearchFilterSort:
    async def _setup_users(self, client: AsyncClient) -> tuple[str, str]:
        token = await register_and_login(client, "search_admin", "search_admin@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        dept = await client.post("/api/departments", json={"name": "搜索测试部"}, headers=headers)
        dept_id = dept.json()["data"]["id"]

        for i in range(3):
            await client.post(
                "/api/users",
                json={
                    "username": f"search_user_{i}",
                    "display_name": f"测试用户{i}",
                    "email": f"search_user_{i}@example.com",
                    "phone": f"1380000001{i}",
                    "department_id": dept_id if i < 2 else None,
                    "role": "student" if i < 2 else "teacher",
                    "password": "password123",
                },
                headers=headers,
            )

        return token, headers

    @pytest.mark.asyncio
    async def test_search_by_username(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?search=search_user_0", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        assert any("search_user_0" in u["username"] for u in items)

    @pytest.mark.asyncio
    async def test_search_by_display_name(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?search=测试用户1", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_search_by_email(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?search=search_user_1@example", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_filter_by_role(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?role=teacher", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for u in items:
            assert u["role"] == "teacher"

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?is_active=true", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for u in items:
            assert u["is_active"] is True

    @pytest.mark.asyncio
    async def test_sort_asc(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?sort_by=username&order=asc&page_size=50", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        usernames = [u["username"] for u in items]
        assert usernames == sorted(usernames)

    @pytest.mark.asyncio
    async def test_sort_desc(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?sort_by=id&order=desc&page_size=50", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        ids = [u["id"] for u in items]
        assert ids == sorted(ids, reverse=True)

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient):
        token, headers = await self._setup_users(client)
        resp = await client.get("/api/users?page=1&page_size=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2


class TestAdminProtection:
    @pytest.mark.asyncio
    async def test_cannot_delete_admin(self, client: AsyncClient):
        token = await register_and_login(client, "protect_admin1", "protect_admin1@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/api/auth/me", headers=headers)
        admin_id = me.json()["data"]["id"]

        resp = await client.delete(f"/api/users/{admin_id}", headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_remove_last_admin_role(self, client: AsyncClient):
        token = await register_and_login(client, "protect_admin2", "protect_admin2@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/api/auth/me", headers=headers)
        admin_id = me.json()["data"]["id"]

        resp = await client.patch(f"/api/users/{admin_id}/role", json={"role": "student"}, headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_can_change_role_when_multiple_admins(self, client: AsyncClient):
        token = await register_and_login(client, "protect_admin3", "protect_admin3@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/api/users",
            json={"username": "second_admin", "email": "second_admin@example.com", "phone": "13800000004", "role": "admin", "password": "password123"},
            headers=headers,
        )
        resp = await client.post("/api/auth/login", json={"username": "second_admin", "password": "password123"})
        admin2_id = resp.json()["data"]["user"]["id"]

        resp = await client.patch(f"/api/users/{admin2_id}/role", json={"role": "student"}, headers=headers)
        assert resp.status_code == 200


class TestUserProfile:
    @pytest.mark.asyncio
    async def test_update_own_profile(self, client: AsyncClient):
        token = await register_and_login(client, "profile_user1", "profile_user1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch("/api/auth/profile", json={"display_name": "新名字"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "新名字"

    @pytest.mark.asyncio
    async def test_update_profile_username_conflict(self, client: AsyncClient):
        await register_and_login(client, "profile_user2", "profile_user2@example.com")
        await client.post("/api/auth/register", json={"username": "existing_user", "email": "existing@example.com", "phone": "13800000009", "password": "password123"})
        resp = await client.post("/api/auth/login", json={"username": "existing_user", "password": "password123"})
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch("/api/auth/profile", json={"username": "profile_user2"}, headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient):
        await client.post("/api/auth/register", json={"username": "pw_user", "email": "pw_user@example.com", "phone": "13800000010", "password": "oldpass123"})
        resp = await client.post("/api/auth/login", json={"username": "pw_user", "password": "oldpass123"})
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/auth/change-password", json={"old_password": "oldpass123", "new_password": "newpass456"}, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client: AsyncClient):
        await client.post("/api/auth/register", json={"username": "pw_user2", "email": "pw_user2@example.com", "phone": "13800000011", "password": "oldpass123"})
        resp = await client.post("/api/auth/login", json={"username": "pw_user2", "password": "oldpass123"})
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/auth/change-password", json={"old_password": "wrongpass", "new_password": "newpass456"}, headers=headers)
        assert resp.status_code == 400


class TestAdminUserManagement:
    @pytest.mark.asyncio
    async def test_admin_create_user(self, client: AsyncClient):
        token = await register_and_login(client, "mgmt_admin1", "mgmt_admin1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/users",
            json={"username": "created_user", "email": "created@example.com", "phone": "13800000020", "role": "teacher", "password": "password123"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["username"] == "created_user"
        assert resp.json()["data"]["role"] == "teacher"

    @pytest.mark.asyncio
    async def test_admin_update_user(self, client: AsyncClient):
        token = await register_and_login(client, "mgmt_admin2", "mgmt_admin2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/users",
            json={"username": "toupdate", "email": "toupdate@example.com", "phone": "13800000021", "role": "student", "password": "password123"},
            headers=headers,
        )
        user_id = created.json()["data"]["id"]

        resp = await client.patch(
            f"/api/users/{user_id}",
            json={"display_name": "更新后名字", "phone": "13900000000"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "更新后名字"
        assert resp.json()["data"]["phone"] == "13900000000"

    @pytest.mark.asyncio
    async def test_admin_reset_password(self, client: AsyncClient):
        token = await register_and_login(client, "mgmt_admin3", "mgmt_admin3@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/users",
            json={"username": "resetpw", "email": "resetpw@example.com", "phone": "13800000022", "role": "student", "password": "password123"},
            headers=headers,
        )
        user_id = created.json()["data"]["id"]

        resp = await client.patch(f"/api/users/{user_id}/password", json={"password": "newpassword"}, headers=headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_non_admin_user(self, client: AsyncClient):
        token = await register_and_login(client, "mgmt_admin4", "mgmt_admin4@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post(
            "/api/users",
            json={"username": "todel_user", "email": "todel_user@example.com", "phone": "13800000023", "role": "student", "password": "password123"},
            headers=headers,
        )
        user_id = created.json()["data"]["id"]

        resp = await client.delete(f"/api/users/{user_id}", headers=headers)
        assert resp.status_code == 200

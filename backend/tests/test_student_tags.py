import pytest
from httpx import AsyncClient


async def _reg_and_login(client: AsyncClient, username: str, role: str = "admin", admin_token: str = "") -> str:
    resp = await client.post(
        "/api/auth/register",
        json={"username": username, "email": f"{username}@test.com", "phone": f"139{abs(hash(username)) % 100000000:08d}", "password": "pwd123"},
    )
    data = resp.json().get("data", {})
    if admin_token and data.get("role") != role:
        await client.patch(
            f"/api/users/{data['id']}/role",
            json={"role": role},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    resp = await client.post("/api/auth/login", json={"username": username, "password": "pwd123"})
    return resp.json()["data"]["access_token"]


async def _create_tag(client: AsyncClient, token: str, name: str) -> dict:
    resp = await client.post("/api/tags", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    return resp.json()


class TestTagCRUD:
    @pytest.mark.asyncio
    async def test_create_and_list_tags(self, client: AsyncClient):
        token = await _reg_and_login(client, "tag_admin1")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/tags", json={"name": "新学员"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "新学员"

        resp = await client.get("/api/tags", headers=headers)
        assert resp.status_code == 200
        tags = resp.json()["data"]
        assert len(tags) >= 1
        assert any(t["name"] == "新学员" for t in tags)

    @pytest.mark.asyncio
    async def test_create_duplicate_tag(self, client: AsyncClient):
        token = await _reg_and_login(client, "tag_admin2")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/tags", json={"name": "重点"}, headers=headers)
        resp = await client.post("/api/tags", json={"name": "重点"}, headers=headers)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_update_tag(self, client: AsyncClient):
        token = await _reg_and_login(client, "tag_admin3")
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post("/api/tags", json={"name": "旧名"}, headers=headers)
        tag_id = created.json()["data"]["id"]

        resp = await client.patch(f"/api/tags/{tag_id}", json={"name": "新名"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "新名"

    @pytest.mark.asyncio
    async def test_delete_tag(self, client: AsyncClient):
        token = await _reg_and_login(client, "tag_admin4")
        headers = {"Authorization": f"Bearer {token}"}
        created = await client.post("/api/tags", json={"name": "待删除"}, headers=headers)
        tag_id = created.json()["data"]["id"]

        resp = await client.delete(f"/api/tags/{tag_id}", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/api/tags", headers=headers)
        assert not any(t["id"] == tag_id for t in resp.json()["data"])

    @pytest.mark.asyncio
    async def test_student_cannot_access_tags(self, client: AsyncClient):
        await _reg_and_login(client, "tag_admin5", "admin")
        stu_tok = await _reg_and_login(client, "tag_stu1", "student")

        resp = await client.get("/api/tags", headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 403

        resp = await client.post("/api/tags", json={"name": "hack"}, headers={"Authorization": f"Bearer {stu_tok}"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_teacher_can_manage_tags(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tag_admin6", "admin")
        tch_tok = await _reg_and_login(client, "tag_tch1", "teacher", admin_tok)
        headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/tags", json={"name": "教师标签"}, headers=headers)
        assert resp.status_code == 201

        resp = await client.get("/api/tags", headers=headers)
        assert resp.status_code == 200
        assert any(t["name"] == "教师标签" for t in resp.json()["data"])


class TestTeacherUserManagement:
    @pytest.mark.asyncio
    async def test_teacher_can_create_student(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin1", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr1", "teacher", admin_tok)
        headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/users", json={
            "username": "tch_stu1", "display_name": "学员A", "email": "tch_stu1@test.com",
            "phone": "13800000001", "role": "student", "password": "pwd123",
        }, headers=headers)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_teacher_cannot_create_teacher(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin2", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr2", "teacher", admin_tok)
        headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/users", json={
            "username": "tch_bad", "display_name": "坏", "email": "tch_bad@test.com",
            "phone": "13800000002", "role": "teacher", "password": "pwd123",
        }, headers=headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_teacher_cannot_modify_teacher(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin3", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr3", "teacher", admin_tok)
        admin_headers = {"Authorization": f"Bearer {admin_tok}"}
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        # create a teacher as admin
        resp = await client.post("/api/users", json={
            "username": "target_tch", "display_name": "目标教师", "email": "target_tch@test.com",
            "phone": "13900000003", "role": "teacher", "password": "pwd123",
        }, headers=admin_headers)
        teacher_id = resp.json()["data"]["id"]

        # teacher tries to modify
        resp = await client.patch(f"/api/users/{teacher_id}", json={"display_name": "改了"}, headers=tch_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_teacher_can_modify_student(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin4", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr4", "teacher", admin_tok)
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/users", json={
            "username": "target_stu", "display_name": "目标学员", "email": "target_stu@test.com",
            "phone": "13900000004", "role": "student", "password": "pwd123",
        }, headers=tch_headers)
        stu_id = resp.json()["data"]["id"]

        resp = await client.patch(f"/api/users/{stu_id}", json={"display_name": "已修改"}, headers=tch_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "已修改"

    @pytest.mark.asyncio
    async def test_teacher_cannot_delete_teacher(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin5", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr5", "teacher", admin_tok)
        admin_headers = {"Authorization": f"Bearer {admin_tok}"}
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/users", json={
            "username": "del_target", "display_name": "待删教师", "email": "del_target@test.com",
            "phone": "13900000005", "role": "teacher", "password": "pwd123",
        }, headers=admin_headers)
        teacher_id = resp.json()["data"]["id"]

        resp = await client.delete(f"/api/users/{teacher_id}", headers=tch_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_teacher_can_delete_student(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin6", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr6", "teacher", admin_tok)
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.post("/api/users", json={
            "username": "del_stu", "display_name": "待删学员", "email": "del_stu@test.com",
            "phone": "13900000006", "role": "student", "password": "pwd123",
        }, headers=tch_headers)
        stu_id = resp.json()["data"]["id"]

        resp = await client.delete(f"/api/users/{stu_id}", headers=tch_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_teacher_list_only_students(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin7", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr7", "teacher", admin_tok)
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.get("/api/users?page_size=999", headers=tch_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for u in items:
            assert u["role"] == "student"

    @pytest.mark.asyncio
    async def test_teacher_role_filter_locked(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "tch_admin8", "admin")
        tch_tok = await _reg_and_login(client, "tch_mgr8", "teacher", admin_tok)
        tch_headers = {"Authorization": f"Bearer {tch_tok}"}

        resp = await client.get("/api/users?role=teacher", headers=tch_headers)
        assert resp.status_code == 403


class TestUserTags:
    @pytest.mark.asyncio
    async def test_assign_tags_to_student(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin1", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        t1 = await client.post("/api/tags", json={"name": "优秀"}, headers=headers)
        t2 = await client.post("/api/tags", json={"name": "需关注"}, headers=headers)
        id1 = t1.json()["data"]["id"]
        id2 = t2.json()["data"]["id"]

        resp = await client.post("/api/users", json={
            "username": "ut_stu1", "display_name": "标签学员", "email": "ut_stu1@test.com",
            "phone": "13900000011", "role": "student", "password": "pwd123",
        }, headers=headers)
        stu_id = resp.json()["data"]["id"]

        resp = await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [id1, id2]}, headers=headers)
        assert resp.status_code == 200

        resp = await client.get(f"/api/users/{stu_id}/tags", headers=headers)
        assert resp.status_code == 200
        tags = resp.json()["data"]
        assert len(tags) == 2
        names = {t["name"] for t in tags}
        assert "优秀" in names
        assert "需关注" in names

        # user list shows tags
        resp = await client.get("/api/users?search=ut_stu1", headers=headers)
        user = resp.json()["data"]["items"][0]
        assert "优秀" in user["tags"]
        assert "需关注" in user["tags"]

        # tags list includes user_count
        resp = await client.get("/api/tags", headers=headers)
        tag_list = resp.json()["data"]
        for t in tag_list:
            if t["name"] == "优秀":
                assert t["user_count"] == 1
            if t["name"] == "需关注":
                assert t["user_count"] == 1

    @pytest.mark.asyncio
    async def test_replace_tags(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin2", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        t1 = await client.post("/api/tags", json={"name": "A"}, headers=headers)
        t2 = await client.post("/api/tags", json={"name": "B"}, headers=headers)
        t3 = await client.post("/api/tags", json={"name": "C"}, headers=headers)
        id1, id2, id3 = t1.json()["data"]["id"], t2.json()["data"]["id"], t3.json()["data"]["id"]

        resp = await client.post("/api/users", json={
            "username": "ut_stu2", "display_name": "替换学员", "email": "ut_stu2@test.com",
            "phone": "13900000012", "role": "student", "password": "pwd123",
        }, headers=headers)
        stu_id = resp.json()["data"]["id"]

        await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [id1, id2]}, headers=headers)
        await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [id2, id3]}, headers=headers)

        resp = await client.get(f"/api/users/{stu_id}/tags", headers=headers)
        tags = resp.json()["data"]
        names = {t["name"] for t in tags}
        assert names == {"B", "C"}

    @pytest.mark.asyncio
    async def test_clear_tags(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin3", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        t1 = await client.post("/api/tags", json={"name": "清空测试"}, headers=headers)
        tid = t1.json()["data"]["id"]

        resp = await client.post("/api/users", json={
            "username": "ut_stu3", "display_name": "清空学员", "email": "ut_stu3@test.com",
            "phone": "13900000013", "role": "student", "password": "pwd123",
        }, headers=headers)
        stu_id = resp.json()["data"]["id"]

        await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [tid]}, headers=headers)
        await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": []}, headers=headers)

        resp = await client.get(f"/api/users/{stu_id}/tags", headers=headers)
        assert len(resp.json()["data"]) == 0

    @pytest.mark.asyncio
    async def test_cannot_tag_non_student(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin4", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        t1 = await client.post("/api/tags", json={"name": "X"}, headers=headers)
        tid = t1.json()["data"]["id"]

        # create a teacher
        resp = await client.post("/api/users", json={
            "username": "ut_tch", "display_name": "教师", "email": "ut_tch@test.com",
            "phone": "13900000014", "role": "teacher", "password": "pwd123",
        }, headers=headers)
        tch_id = resp.json()["data"]["id"]

        resp = await client.put(f"/api/users/{tch_id}/tags", json={"tag_ids": [tid]}, headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_tag_id(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin5", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        resp = await client.post("/api/users", json={
            "username": "ut_stu5", "display_name": "错误学员", "email": "ut_stu5@test.com",
            "phone": "13900000015", "role": "student", "password": "pwd123",
        }, headers=headers)
        stu_id = resp.json()["data"]["id"]

        resp = await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [99999]}, headers=headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_tag_cascades_links(self, client: AsyncClient):
        admin_tok = await _reg_and_login(client, "ut_admin6", "admin")
        headers = {"Authorization": f"Bearer {admin_tok}"}

        t1 = await client.post("/api/tags", json={"name": "待删除关联"}, headers=headers)
        tid = t1.json()["data"]["id"]

        resp = await client.post("/api/users", json={
            "username": "ut_stu6", "display_name": "级联学员", "email": "ut_stu6@test.com",
            "phone": "13900000016", "role": "student", "password": "pwd123",
        }, headers=headers)
        stu_id = resp.json()["data"]["id"]
        await client.put(f"/api/users/{stu_id}/tags", json={"tag_ids": [tid]}, headers=headers)

        await client.delete(f"/api/tags/{tid}", headers=headers)

        resp = await client.get(f"/api/users/{stu_id}/tags", headers=headers)
        assert len(resp.json()["data"]) == 0

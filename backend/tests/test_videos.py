import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import Video, VideoViewRecord


async def _reg_admin(client: AsyncClient) -> str:
    await client.post("/api/auth/register", json={
        "username": "vid_admin", "email": "vid_admin@test.com",
        "phone": "13900001111", "department": "Dept", "password": "pwd123",
    })
    resp = await client.post("/api/auth/login", json={"username": "vid_admin", "password": "pwd123"})
    return resp.json()["data"]["access_token"]


class TestVideoStatsRegenerate:
    @pytest.mark.asyncio
    async def test_regenerate_updates_counters(self, client: AsyncClient, db_session: AsyncSession):
        token = await _reg_admin(client)
        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        admin_id = me.json()["data"]["id"]

        video = Video(name="v1", oss_path="videos/v1.mp4", created_by=admin_id, total_views=0, total_watch_seconds=0)
        db_session.add(video)
        await db_session.flush()

        # Two view records; counters were never incremented (drift scenario).
        db_session.add_all([
            VideoViewRecord(video_id=video.id, user_id=admin_id, watch_seconds=30),
            VideoViewRecord(video_id=video.id, user_id=admin_id, watch_seconds=45),
        ])
        await db_session.commit()

        resp = await client.post(f"/api/videos/{video.id}/stats/regenerate", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_views"] == 2
        assert data["total_watch_seconds"] == 75

    @pytest.mark.asyncio
    async def test_regenerate_not_found(self, client: AsyncClient):
        token = await _reg_admin(client)
        resp = await client.post("/api/videos/999999/stats/regenerate", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

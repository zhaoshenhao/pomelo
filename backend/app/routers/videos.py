import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies.auth import get_current_user, require_student, require_teacher_or_admin
from app.models.document import DocumentLibrary
from app.models.user import User
from app.models.video import Video, VideoComment, VideoViewRecord
from app.schemas.common import success_response
from app.schemas.video import (
    VideoCommentCreate,
    VideoCommentItem,
    VideoCommentListResponse,
    VideoCreateFromOss,
    VideoDeleteRequest,
    VideoDetailResponse,
    VideoListItem,
    VideoListResponse,
    VideoMyItem,
    VideoStatsResponse,
    VideoUpdateRequest,
    VideoUploadResult,
    VideoViewRecordItem,
    VideoWatchReport,
)
from app.services.oss_service import (
    delete_object_async,
    download_to_temp_async,
    list_first_level_dirs_async,
    list_objects_async,
    object_exists_async,
    sign_url,
    upload_async,
)
from app.services.video_service import probe_duration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


async def _resolve_names(session, lib_ids: set, user_ids: set) -> tuple[dict, dict]:
    lib_map = {}
    user_map = {}
    if lib_ids:
        r = await session.execute(select(DocumentLibrary.id, DocumentLibrary.name).where(DocumentLibrary.id.in_(lib_ids)))
        lib_map = {lid: lname for lid, lname in r}
    if user_ids:
        r = await session.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
        user_map = {uid: uname for uid, uname in r}
    return lib_map, user_map


def _format_dt(dt) -> str:
    if dt is None:
        return ""
    return dt.isoformat()


# ==================== Teacher/Admin endpoints ====================


@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    base = select(Video)
    if search:
        base = base.where(Video.name.ilike(f"%{search}%") | Video.description.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    rows = await session.execute(base.order_by(Video.id.desc()).offset(offset).limit(page_size))
    videos = rows.scalars().all()

    lib_ids = {v.library_id for v in videos if v.library_id is not None}
    user_ids = {v.created_by for v in videos}
    lib_map, user_map = await _resolve_names(session, lib_ids, user_ids)

    items = [
        VideoListItem(
            id=v.id, name=v.name, description=v.description,
            library_id=v.library_id, library_name=lib_map.get(v.library_id, ""),
            creator_name=user_map.get(v.created_by, ""),
            duration_seconds=v.duration_seconds, active=v.active,
            source=v.source, oss_path=v.oss_path, original_filename=v.original_filename,
            total_views=v.total_views, total_watch_seconds=v.total_watch_seconds,
            created_at=v.created_at, updated_at=v.updated_at,
        )
        for v in videos
    ]
    return success_response(VideoListResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/oss/dirs")
async def get_oss_dirs(_: User = Depends(require_teacher_or_admin)):
    try:
        return success_response(await list_first_level_dirs_async())
    except Exception as e:
        logger.warning("OSS dirs error: %s", e)
        return success_response([])


@router.get("/oss/objects")
async def get_oss_objects(
    prefix: str = Query(""),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        return success_response(await list_objects_async(prefix))
    except Exception as e:
        logger.warning("OSS objects error: %s", e)
        return success_response([])


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    name: str = Query(""),
    description: str = Query(""),
    library_id: int | None = Query(None),
    active: bool = Query(True),
    oss_dir: str = Query(""),
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未选择文件")

    safe_name = file.filename.replace("\\", "/").split("/")[-1]
    base = f"{oss_dir}/{safe_name}" if oss_dir else safe_name
    full_key = (settings.OSS_VIDEO_PREFIX + base).replace("//", "/")

    if await object_exists_async(full_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OSS路径 {full_key} 已存在，请更换名称或路径")

    content = await file.read()
    try:
        await upload_async(full_key, content, len(content))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OSS上传失败: {e}")

    tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(safe_name)[1] or ".mp4", delete=False)
    tmp.write(content)
    tmp.close()

    try:
        dur = probe_duration(tmp.name)
    except Exception:
        dur = 0
    finally:
        os.unlink(tmp.name)

    video = Video(
        name=name or safe_name,
        description=description,
        library_id=library_id,
        created_by=current_user.id,
        duration_seconds=dur,
        active=active,
        source="local",
        oss_path=full_key,
        original_filename=file.filename,
    )
    session.add(video)
    await session.commit()
    await session.refresh(video)

    return success_response(VideoUploadResult(
        id=video.id, name=video.name, oss_path=full_key, duration_seconds=dur,
    ), "上传成功")


@router.post("/from-oss")
async def create_from_oss(
    request: VideoCreateFromOss,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    dur = 0
    tmp = None
    try:
        tmp = await download_to_temp_async(request.oss_path)
        dur = probe_duration(tmp)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OSS访问失败: {e}")
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    video = Video(
        name=request.name,
        description=request.description,
        library_id=request.library_id,
        created_by=current_user.id,
        duration_seconds=dur,
        active=request.active,
        source="oss",
        oss_path=request.oss_path,
    )
    session.add(video)
    await session.commit()
    await session.refresh(video)

    return success_response(VideoUploadResult(id=video.id, name=video.name, oss_path=request.oss_path, duration_seconds=dur), "创建成功")


@router.get("/{video_id}")
async def get_video(
    video_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    lib_ids = {v.library_id} if v.library_id is not None else set()
    user_ids = {v.created_by}
    lib_map, user_map = await _resolve_names(session, lib_ids, user_ids)
    return success_response(VideoDetailResponse(
        id=v.id, name=v.name, description=v.description,
        library_id=v.library_id, library_name=lib_map.get(v.library_id, ""),
        creator_name=user_map.get(v.created_by, ""),
        duration_seconds=v.duration_seconds, active=v.active,
        source=v.source, oss_path=v.oss_path, original_filename=v.original_filename,
        total_views=v.total_views, total_watch_seconds=v.total_watch_seconds,
        created_at=v.created_at, updated_at=v.updated_at,
    ))


@router.put("/{video_id}")
async def update_video(
    video_id: int,
    request: VideoUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="名称不能为空")
        v.name = request.name
    if request.description is not None:
        v.description = request.description
    if "library_id" in request.model_fields_set:
        v.library_id = request.library_id
    if request.active is not None:
        v.active = request.active
    await session.commit()
    return success_response(None, "更新成功")


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    request: VideoDeleteRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    if request.delete_oss and v.oss_path:
        try:
            await delete_object_async(v.oss_path)
        except Exception as e:
            logger.warning("Failed to delete OSS object: %s", e)

    comments = (await session.execute(select(VideoComment).where(VideoComment.video_id == video_id))).scalars().all()
    for c in comments:
        await session.delete(c)
    records = (await session.execute(select(VideoViewRecord).where(VideoViewRecord.video_id == video_id))).scalars().all()
    for r in records:
        await session.delete(r)

    await session.delete(v)
    await session.commit()
    return success_response(None, "删除成功")


@router.get("/{video_id}/play-url")
async def video_play_url(video_id: int, session: AsyncSession = Depends(get_session), _: User = Depends(get_current_user)):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    url = sign_url(v.oss_path)
    return success_response({"url": url})


@router.get("/{video_id}/comments")
async def list_comments(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    base = select(VideoComment).where(VideoComment.video_id == video_id)
    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0
    rows = await session.execute(base.order_by(VideoComment.id.desc()).offset((page - 1) * page_size).limit(page_size))
    comments = rows.scalars().all()
    user_ids = {c.user_id for c in comments}
    _, user_map = await _resolve_names(session, set(), user_ids)
    items = [
        VideoCommentItem(id=c.id, video_id=c.video_id, user_id=c.user_id, username=user_map.get(c.user_id, ""), content=c.content, created_at=_format_dt(c.created_at))
        for c in comments
    ]
    return success_response(VideoCommentListResponse(items=items, total=total, page=page, page_size=page_size))


@router.post("/{video_id}/comments")
async def add_comment(
    video_id: int,
    request: VideoCommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    comment = VideoComment(video_id=video_id, user_id=current_user.id, content=request.content)
    session.add(comment)
    await session.commit()
    return success_response(None, "留言成功")


@router.get("/{video_id}/stats")
async def video_stats(
    video_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    viewers_q = select(func.count(func.distinct(VideoViewRecord.user_id))).where(VideoViewRecord.video_id == video_id)
    total_viewers = (await session.execute(viewers_q)).scalar() or 0

    view_records_base = select(VideoViewRecord).where(VideoViewRecord.video_id == video_id)
    vr_count = (await session.execute(select(func.count()).select_from(view_records_base.subquery()))).scalar() or 0
    vr_rows = await session.execute(view_records_base.order_by(VideoViewRecord.watched_at.desc()).offset((page - 1) * page_size).limit(page_size))
    records = vr_rows.scalars().all()
    user_ids = {r.user_id for r in records}
    _, user_map = await _resolve_names(session, set(), user_ids)
    vr_items = [
        VideoViewRecordItem(watched_at=_format_dt(r.watched_at), username=user_map.get(r.user_id, ""), watch_seconds=r.watch_seconds)
        for r in records
    ]

    stats = VideoStatsResponse(
        video_id=v.id, video_name=v.name,
        total_viewers=total_viewers,
        total_views=v.total_views,
        total_watch_seconds=v.total_watch_seconds,
    )

    comments_base = select(VideoComment).where(VideoComment.video_id == video_id)
    cmt_count = (await session.execute(select(func.count()).select_from(comments_base.subquery()))).scalar() or 0
    cmt_rows = await session.execute(comments_base.order_by(VideoComment.id.desc()).offset((page - 1) * page_size).limit(page_size))
    cmts = cmt_rows.scalars().all()
    cmt_user_ids = {c.user_id for c in cmts}
    _, cmt_user_map = await _resolve_names(session, set(), cmt_user_ids)
    cmt_items = [
        VideoCommentItem(id=c.id, video_id=c.video_id, user_id=c.user_id, username=cmt_user_map.get(c.user_id, ""), content=c.content, created_at=_format_dt(c.created_at))
        for c in cmts
    ]

    return success_response({
        "stats": stats.model_dump(),
        "view_records": {"items": [vi.model_dump() for vi in vr_items], "total": vr_count, "page": page, "page_size": page_size},
        "comments": {"items": [ci.model_dump() for ci in cmt_items], "total": cmt_count, "page": page, "page_size": page_size},
    })


@router.post("/{video_id}/stats/regenerate")
async def regenerate_video_stats(
    video_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")

    total_views = (await session.execute(
        select(func.count()).select_from(VideoViewRecord).where(VideoViewRecord.video_id == video_id)
    )).scalar() or 0
    total_watch = (await session.execute(
        select(func.coalesce(func.sum(VideoViewRecord.watch_seconds), 0)).where(VideoViewRecord.video_id == video_id)
    )).scalar() or 0

    v.total_views = int(total_views)
    v.total_watch_seconds = int(total_watch)
    await session.commit()

    return success_response({"total_views": v.total_views, "total_watch_seconds": v.total_watch_seconds}, "已重新汇总")


# ==================== Student endpoints ====================


@router.get("/my/list")
async def my_videos(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    videos = (await session.execute(
        select(Video).where(Video.active).order_by(Video.id.desc())
    )).scalars().all()

    if not videos:
        return success_response([])

    video_ids = [v.id for v in videos]
    records = (await session.execute(
        select(VideoViewRecord).where(
            VideoViewRecord.video_id.in_(video_ids),
            VideoViewRecord.user_id == current_user.id,
        )
    )).scalars().all()

    per_vid: dict[int, list[VideoViewRecord]] = {}
    for r in records:
        per_vid.setdefault(r.video_id, []).append(r)

    lib_ids = {v.library_id for v in videos if v.library_id is not None}
    lib_map, _ = await _resolve_names(session, lib_ids, set())

    items = []
    for v in videos:
        recs = per_vid.get(v.id, [])
        watched = len(recs) > 0
        my_views = len(recs)
        my_seconds = sum(r.watch_seconds for r in recs)
        last_ts = max(r.watched_at for r in recs) if recs else None
        items.append(VideoMyItem(
            id=v.id, name=v.name, description=v.description,
            library_id=v.library_id, library_name=lib_map.get(v.library_id, ""),
            duration_seconds=v.duration_seconds,
            watched=watched, my_views=my_views, my_watch_seconds=my_seconds,
            last_watched_at=_format_dt(last_ts) if last_ts else None,
        ))

    return success_response(items)


@router.post("/{video_id}/watch")
async def report_watch(
    video_id: int,
    request: VideoWatchReport,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    v = (await session.execute(select(Video).where(Video.id == video_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频不存在")
    record = VideoViewRecord(
        video_id=video_id, user_id=current_user.id,
        watch_seconds=request.watch_seconds,
    )
    session.add(record)
    v.total_views += 1
    v.total_watch_seconds += request.watch_seconds
    await session.commit()
    return success_response(None, "已记录")

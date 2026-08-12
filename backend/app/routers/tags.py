import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_teacher_or_admin
from app.models.student_tag import StudentTag, student_tag_links
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.tag import TagCreateRequest, TagResponse, TagUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
async def list_tags(
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_teacher_or_admin),
):
    result = await session.execute(select(StudentTag).order_by(StudentTag.id))
    tags = result.scalars().all()

    tag_ids = [t.id for t in tags]
    counts = {}
    if tag_ids:
        count_result = await session.execute(
            select(
                student_tag_links.c.tag_id,
                func.count(student_tag_links.c.user_id),
            )
            .where(student_tag_links.c.tag_id.in_(tag_ids))
            .group_by(student_tag_links.c.tag_id)
        )
        counts = {row[0]: row[1] for row in count_result.all()}

    items = []
    for t in tags:
        d = TagResponse.model_validate(t)
        d.user_count = counts.get(t.id, 0)
        items.append(d)

    return success_response(items)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: TagCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    existing = await session.execute(
        select(StudentTag).where(StudentTag.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签名称已存在")

    tag = StudentTag(name=request.name, created_by=current_user.id)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)

    return success_response(TagResponse.model_validate(tag), "标签创建成功")


@router.patch("/{tag_id}")
async def update_tag(
    tag_id: int,
    request: TagUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_teacher_or_admin),
):
    tag = await session.get(StudentTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")

    dup = await session.execute(
        select(StudentTag).where(
            StudentTag.name == request.name, StudentTag.id != tag_id
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="标签名称已存在")

    tag.name = request.name
    await session.commit()
    await session.refresh(tag)

    return success_response(TagResponse.model_validate(tag), "标签已更新")


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_teacher_or_admin),
):
    tag = await session.get(StudentTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")

    await session.delete(tag)
    await session.commit()

    return success_response(None, "标签已删除")

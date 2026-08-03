from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_admin
from app.models.rewrite_style import RewriteStyle
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.rewrite_style import (
    RewriteStyleCreateRequest,
    RewriteStyleResponse,
    RewriteStyleUpdateRequest,
)

router = APIRouter(prefix="/rewrite-styles", tags=["rewrite_styles"])


@router.get("")
async def list_rewrite_styles(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(RewriteStyle).order_by(RewriteStyle.id))
    styles = result.scalars().all()
    return success_response([RewriteStyleResponse.model_validate(s) for s in styles])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rewrite_style(
    request: RewriteStyleCreateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(select(RewriteStyle).where(RewriteStyle.name == request.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="改写风格名称已存在")
    style = RewriteStyle(name=request.name, prompt=request.prompt)
    session.add(style)
    await session.commit()
    await session.refresh(style)
    return success_response(RewriteStyleResponse.model_validate(style), "创建成功")


@router.put("/{style_id}")
async def update_rewrite_style(
    style_id: int,
    request: RewriteStyleUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(RewriteStyle).where(RewriteStyle.id == style_id))
    style = result.scalar_one_or_none()
    if style is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="改写风格不存在")
    if request.name is not None:
        existing = await session.execute(
            select(RewriteStyle).where(RewriteStyle.name == request.name, RewriteStyle.id != style_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="改写风格名称已存在")
        style.name = request.name
    if request.prompt is not None:
        style.prompt = request.prompt
    await session.commit()
    await session.refresh(style)
    return success_response(RewriteStyleResponse.model_validate(style), "更新成功")


@router.delete("/{style_id}")
async def delete_rewrite_style(
    style_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(RewriteStyle).where(RewriteStyle.id == style_id))
    style = result.scalar_one_or_none()
    if style is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="改写风格不存在")
    await session.delete(style)
    await session.commit()
    return success_response(None, "删除成功")

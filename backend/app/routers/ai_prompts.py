from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_admin
from app.models.ai_prompt import AIPrompt
from app.models.user import User
from app.schemas.ai_prompt import (
    AIPromptCreateRequest,
    AIPromptResponse,
    AIPromptUpdateRequest,
)
from app.schemas.common import success_response

router = APIRouter(prefix="/ai-prompts", tags=["ai_prompts"])


@router.get("")
async def list_ai_prompts(
    prompt_type: str | None = Query(None, alias="type"),
    session: AsyncSession = Depends(get_session),
):
    query = select(AIPrompt).order_by(AIPrompt.id)
    if prompt_type:
        query = query.where(AIPrompt.prompt_type == prompt_type)
    result = await session.execute(query)
    prompts = result.scalars().all()
    return success_response([AIPromptResponse.model_validate(p) for p in prompts])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ai_prompt(
    request: AIPromptCreateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(
        select(AIPrompt).where(
            AIPrompt.name == request.name,
            AIPrompt.prompt_type == request.prompt_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同类型下提示词名称已存在")
    prompt = AIPrompt(name=request.name, prompt=request.prompt, prompt_type=request.prompt_type)
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)
    return success_response(AIPromptResponse.model_validate(prompt), "创建成功")


@router.put("/{prompt_id}")
async def update_ai_prompt(
    prompt_id: int,
    request: AIPromptUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI提示词不存在")
    name = request.name if request.name is not None else prompt.name
    typ = request.prompt_type if request.prompt_type is not None else prompt.prompt_type
    existing = await session.execute(
        select(AIPrompt).where(
            AIPrompt.name == name,
            AIPrompt.prompt_type == typ,
            AIPrompt.id != prompt_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同类型下提示词名称已存在")
    if request.name is not None:
        prompt.name = request.name
    if request.prompt is not None:
        prompt.prompt = request.prompt
    if request.prompt_type is not None:
        prompt.prompt_type = request.prompt_type
    await session.commit()
    await session.refresh(prompt)
    return success_response(AIPromptResponse.model_validate(prompt), "更新成功")


@router.delete("/{prompt_id}")
async def delete_ai_prompt(
    prompt_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(AIPrompt).where(AIPrompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI提示词不存在")
    await session.delete(prompt)
    await session.commit()
    return success_response(None, "删除成功")

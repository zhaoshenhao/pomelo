from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user, require_admin
from app.models.department import Department
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.department import DepartmentCreateRequest, DepartmentResponse, DepartmentUpdateRequest

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
async def list_departments(
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Department).order_by(Department.id))
    departments = result.scalars().all()

    items = []
    for dept in departments:
        count_result = await session.execute(
            select(func.count(User.id)).where(User.department_id == dept.id)
        )
        user_count = count_result.scalar() or 0
        items.append(
            DepartmentResponse(
                id=dept.id,
                name=dept.name,
                user_count=user_count,
                created_at=dept.created_at,
                updated_at=dept.updated_at,
            )
        )

    return success_response(items)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(
    request: DepartmentCreateRequest,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_admin),
):
    existing = await session.execute(
        select(Department).where(Department.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门名称已存在")

    dept = Department(name=request.name)
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return success_response(
        DepartmentResponse(
            id=dept.id,
            name=dept.name,
            user_count=0,
            created_at=dept.created_at,
            updated_at=dept.updated_at,
        ),
        "部门创建成功",
    )


@router.patch("/{department_id}")
async def update_department(
    department_id: int,
    request: DepartmentUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_admin),
):
    dept = await session.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")

    dup = await session.execute(
        select(Department).where(
            Department.name == request.name, Department.id != department_id
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门名称已存在")

    dept.name = request.name
    await session.commit()
    await session.refresh(dept)
    return success_response(
        DepartmentResponse(
            id=dept.id,
            name=dept.name,
            user_count=0,
            created_at=dept.created_at,
            updated_at=dept.updated_at,
        ),
        "部门更新成功",
    )


@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    session: AsyncSession = Depends(get_session),
    _current_user: User = Depends(require_admin),
):
    dept = await session.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")

    user_count_result = await session.execute(
        select(func.count(User.id)).where(User.department_id == department_id)
    )
    user_count = user_count_result.scalar() or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该部门下有 {user_count} 个用户，无法删除",
        )

    await session.delete(dept)
    await session.commit()
    return success_response(None, "部门已删除")

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.database import get_session
from app.dependencies.auth import get_current_user, hash_password, require_admin, require_teacher_or_admin
from app.models.department import Department
from app.models.student_tag import StudentTag, student_tag_links
from app.models.user import User, UserRole
from app.schemas.common import success_response
from app.schemas.tag import UserTagsUpdateRequest
from app.schemas.user import (
    UserCreateRequest,
    UserListResponse,
    UserPasswordResetRequest,
    UserResponse,
    UserRoleUpdateRequest,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["users"])


def _user_to_response(user: User, department_name: str | None = None) -> UserResponse:
    tag_names = [t.name for t in user.tags] if hasattr(user, "tags") and user.tags else []
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        department_id=user.department_id,
        department_name=department_name,
        role=user.role.value if isinstance(user.role, UserRole) else user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        tags=tag_names,
    )


SORT_WHITELIST = {"id", "username", "display_name", "email", "role", "department", "is_active"}


@router.get("")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    role: str = "",
    is_active: str = "",
    sort_by: str = "id",
    order: str = "asc",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要教师或管理员权限")

    if current_user.role == UserRole.TEACHER:
        if role and role != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师只能查看学员")
        role = "student"

    query = select(User).options(joinedload(User.department), selectinload(User.tags))

    if search:
        like = f"%{search}%"
        query = query.where(
            (User.username.ilike(like))
            | (User.email.ilike(like))
            | (User.display_name.ilike(like))
        )

    if role and role in [r.value for r in UserRole]:
        query = query.where(User.role == UserRole(role))

    if is_active in ("true", "false"):
        query = query.where(User.is_active == (is_active == "true"))

    sort_column_map = {
        "id": User.id,
        "username": User.username,
        "display_name": User.display_name,
        "email": User.email,
        "role": User.role,
        "department": User.department_id,
        "is_active": User.is_active,
    }
    sort_column = sort_column_map.get(sort_by, User.id)
    if order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    users = result.unique().scalars().all()

    items = [_user_to_response(u, u.department.name if u.department else None) for u in users]

    return success_response(
        UserListResponse(items=items, total=total, page=page, page_size=page_size)
    )


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).options(joinedload(User.department), selectinload(User.tags)).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return success_response(
        _user_to_response(user, user.department.name if user.department else None)
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    if request.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色类型")

    if current_user.role == UserRole.TEACHER and request.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师只能创建学员")

    existing = await session.execute(
        select(User).where(
            (User.username == request.username) | (User.email == request.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已存在")

    if request.department_id is not None:
        dept = await session.get(Department, request.department_id)
        if dept is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门不存在")

    user = User(
        username=request.username,
        display_name=request.display_name or request.username,
        email=request.email,
        phone=request.phone,
        department_id=request.department_id,
        hashed_password=hash_password(request.password),
        role=UserRole(request.role),
        is_active=request.is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return success_response(UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        department_id=user.department_id,
        department_name=user.department.name if user.department else None,
        role=user.role.value if isinstance(user.role, UserRole) else user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        tags=[t.name for t in user.tags],
    ), "用户创建成功")


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).options(joinedload(User.department), selectinload(User.tags)).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if current_user.role == UserRole.TEACHER:
        if user.role != UserRole.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师只能管理学员")
        if request.role is not None and request.role != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="教师不能修改学员角色")

    if request.username is not None and request.username != user.username:
        dup = await session.execute(select(User).where(User.username == request.username))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    if request.email is not None and request.email != user.email:
        dup = await session.execute(select(User).where(User.email == request.email))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")

    if request.department_id is not None:
        dept = await session.get(Department, request.department_id)
        if dept is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门不存在")

    if request.role is not None and request.role != user.role.value:
        if request.role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色类型")
        if user.role == UserRole.ADMIN and request.role != "admin":
            remaining = await session.execute(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.id != user.id)
            )
            if remaining.scalar() == 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除最后一个管理员")

    if request.is_active is False and user.role == UserRole.ADMIN:
        remaining = await session.execute(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.is_active, User.id != user.id)
        )
        if remaining.scalar() == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能停用最后一个管理员")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role":
            setattr(user, "role", UserRole(value))
        else:
            setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    dept_name = None
    if user.department_id:
        dept = await session.get(Department, user.department_id)
        dept_name = dept.name if dept else None

    return success_response(_user_to_response(user, dept_name), "用户信息更新成功")


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UserRoleUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if request.role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的角色类型")
    result = await session.execute(
        select(User).options(joinedload(User.department)).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.role == UserRole.ADMIN and request.role != "admin":
        remaining = await session.execute(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.id != user.id)
        )
        if remaining.scalar() == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除最后一个管理员")

    user.role = UserRole(request.role)
    await session.commit()
    await session.refresh(user)
    return success_response(
        _user_to_response(user, user.department.name if user.department else None), "角色更新成功"
    )


@router.patch("/{user_id}/password")
async def reset_user_password(
    user_id: int,
    request: UserPasswordResetRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if current_user.role == UserRole.TEACHER and user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师只能管理学员")

    user.hashed_password = hash_password(request.password)
    await session.commit()
    return success_response(None, "密码已重置")


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if current_user.role == UserRole.TEACHER and user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="教师只能管理学员")

    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除管理员用户")
    await session.delete(user)
    await session.commit()
    return success_response(None, "用户已删除")


@router.get("/{user_id}/tags")
async def get_user_tags(
    user_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).options(selectinload(User.tags)).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能查看学员的标签")

    tags = [{"id": t.id, "name": t.name} for t in user.tags]
    return success_response(tags)


@router.put("/{user_id}/tags")
async def set_user_tags(
    user_id: int,
    request: UserTagsUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).options(selectinload(User.tags)).where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能给学员打标签")

    tag_ids = list(set(request.tag_ids))
    if tag_ids:
        tags = (await session.execute(
            select(StudentTag).where(StudentTag.id.in_(tag_ids))
        )).scalars().all()
        if len(tags) != len(tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="包含不存在的标签ID")

    await session.execute(
        delete(student_tag_links).where(student_tag_links.c.user_id == user_id)
    )
    for tid in tag_ids:
        await session.execute(
            student_tag_links.insert().values(user_id=user_id, tag_id=tid)
        )
    await session.commit()

    return success_response(None, "标签已更新")

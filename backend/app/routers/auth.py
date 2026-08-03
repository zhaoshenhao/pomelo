import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_session
from app.dependencies.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    oauth2_scheme,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.common import success_response
from app.schemas.user import (
    ChangePasswordRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
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
    )


async def _create_session_for_user(user_id: int) -> str:
    try:
        from app.services.redis_store import create_session

        return await create_session(user_id)
    except Exception as e:
        logger.warning("Redis unavailable, creating session-less token: %s", e)
        return ""


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(
        select(User).where((User.username == request.username) | (User.email == request.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已存在")

    first_user = await session.execute(select(User).limit(1))
    role = UserRole.ADMIN if first_user.scalar_one_or_none() is None else UserRole.STUDENT

    user = User(
        username=request.username,
        display_name=request.display_name or request.username,
        email=request.email,
        phone=request.phone,
        department_id=request.department_id,
        hashed_password=hash_password(request.password),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return success_response(UserResponse.model_validate(user), "注册成功")


@router.post("/login")
async def login(request: UserLoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(User).options(joinedload(User.department)).where(User.username == request.username)
    )
    user = result.unique().scalar_one_or_none()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    session_id = await _create_session_for_user(user.id)
    access_token = create_access_token(user.id, user.role.value, jti=session_id)
    refresh_token = create_refresh_token(user.id)
    return success_response(
        LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=_user_to_response(user),
        )
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest, session: AsyncSession = Depends(get_session)):
    refresh_payload = decode_token(request.refresh_token)
    if refresh_payload is None or refresh_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭证无效或已过期")

    user_id = refresh_payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭证无效")

    old_access_payload = decode_token(request.access_token)
    old_jti = old_access_payload.get("jti") if old_access_payload else None

    if old_jti:
        try:
            from app.services.redis_store import delete_session, get_session

            existing = await get_session(old_jti)
            if existing is None:
                logger.warning(
                    "Refresh replay detected for user_id=%s jti=%s — force logout",
                    user_id,
                    old_jti,
                )
                try:
                    from app.services.redis_store import delete_user_sessions

                    await delete_user_sessions(int(user_id))
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="刷新凭证已被使用，请重新登录",
                )
            await delete_session(old_jti)
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Session operation failed during refresh: %s", e)

    result = await session.execute(
        select(User).options(joinedload(User.department)).where(User.id == int(user_id))
    )
    user = result.unique().scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用")

    new_session_id = await _create_session_for_user(user.id)
    access_token = create_access_token(user.id, user.role.value, jti=new_session_id)
    new_refresh_token = create_refresh_token(user.id)
    return success_response(TokenResponse(access_token=access_token, refresh_token=new_refresh_token))


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    if token:
        payload = decode_token(token)
        jti = payload.get("jti") if payload else None
        if jti:
            try:
                from app.services.redis_store import delete_session

                await delete_session(jti)
            except Exception as e:
                logger.warning("Failed to delete session on logout: %s", e)
    return success_response(None, "已登出")


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return success_response(UserResponse.model_validate(user))


@router.patch("/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).options(joinedload(User.department)).where(User.id == current_user.id)
    )
    user = result.unique().scalar_one_or_none()

    if request.username is not None and request.username != user.username:
        dup = await session.execute(select(User).where(User.username == request.username))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    if request.email is not None and request.email != user.email:
        dup = await session.execute(select(User).where(User.email == request.email))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return success_response(_user_to_response(user), "个人信息更新成功")


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    user.hashed_password = hash_password(request.new_password)
    await session.commit()

    try:
        from app.services.redis_store import delete_user_sessions

        await delete_user_sessions(current_user.id)
    except Exception as e:
        logger.warning("Failed to revoke sessions after password change: %s", e)

    return success_response(None, "密码修改成功")
